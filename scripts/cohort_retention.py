# Insight 2 (exploratory): do new contributors to the AI ecosystem stay? Weekly cohort retention.
# Window 2025-03-01 .. 2025-05-16 = 11 full 7-day blocks (block 0..10); 05-17..05-22 is a partial block and is dropped.
# Left-censoring: we have no data before 2025-03-01, so anyone active in blocks 0-1 is treated as an EXISTING contributor
# ("burn-in"); a "new" contributor is first seen in block c >= 2. Someone returning after >2 quiet weeks still looks new.
# Contributor = any non-bot actor with a Push/PR/Issue/comment/review event on a candidate AI repo (not star/fork).
# Retention(c, k) = share of cohort c active again in block c+k (anywhere in the AI repo set, not the same repo).
# Usage: python -I -X utf8 scripts/cohort_retention.py
import duckdb, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
PQ, OUT = f"{ROOT}/data/parquet", f"{ROOT}/data/derived"
files = f"['{PQ}/2025-03-*.parquet', '{PQ}/2025-04-*.parquet', '{PQ}/2025-05-*.parquet']"
TYPES = "('PushEvent','PullRequestEvent','IssuesEvent','IssueCommentEvent','PullRequestReviewEvent','PullRequestReviewCommentEvent')"
BURN_IN, LAST = 2, 10  # blocks 0..1 = burn-in; last full block = 10

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4; set max_temp_directory_size='5GB'")
con.execute(f"set temp_directory='{ROOT}/data/duck_tmp'")
t = time.time()
def lap(msg): print(f"[{time.time()-t:4.0f}s] {msg}", flush=True)

con.execute(f"create table cand as select repo from read_parquet('{OUT}/ai_repo_universe.parquet')")
# one row per (actor, block): small table; 'code' = did any Push/PR that block
con.execute(f"""create table ab as
  select actor, ((ts::date - date '2025-03-01') // 7)::int blk, bool_or(type in ('PushEvent','PullRequestEvent')) code
  from read_parquet({files})
  where ts >= '2025-03-01' and ts < '2025-05-17' and type in {TYPES} and actor is not null
    and repo in (select repo from cand)
    and actor not ilike '%[bot]' and actor not ilike '%-bot'
  group by 1, 2""")
lap(f"(actor, block) rows: {con.sql('select count(*) from ab').fetchone()[0]:,}, "
    f"distinct contributors: {con.sql('select count(distinct actor) from ab').fetchone()[0]:,}")
print("\nActive contributors per block (context):")
con.sql("select blk, count(*) active, count(*) filter (code) with_code from ab group by 1 order by 1").show(max_rows=15)

con.execute(f"""create table cohort as
  select a.actor, f.c, a.code first_is_code from ab a
  join (select actor, min(blk) c from ab group by 1) f on a.actor = f.actor and a.blk = f.c
  where f.c >= {BURN_IN} and f.c <= {LAST} - 1""")
con.execute("""create table ret as
  select c.c, k.k, count(*) size, count(*) filter (exists (select 1 from ab x where x.actor = c.actor and x.blk = c.c + k.k)) kept,
         c.first_is_code
  from cohort c cross join (select unnest(range(1, 9)) k) k
  where c.c + k.k <= %d group by all""" % LAST)
con.execute(f"copy ret to '{OUT}/cohort_retention.parquet' (format parquet)")

def triangle(where, title):
    print(f"\n{title}  (rows = cohort block of first activity; cols = blocks later; value = % of cohort active again)")
    cols = ", ".join(f"round(100.0 * sum(kept) filter (k = {k}) / nullif(sum(size) filter (k = {k}), 0), 1) \"+{k}w\"" for k in range(1, 9))
    con.sql(f"select c cohort_blk, sum(size) filter (k = 1) cohort_size, {cols} from ret {where} group by c order by c").show(max_rows=12)
triangle("", "ALL new contributors")
triangle("where first_is_code", "FIRST activity = code (push / PR)")
triangle("where not first_is_code", "FIRST activity = issue / comment / review only")
print("Pooled retention across cohorts (weighted by cohort size):")
con.sql("""select k "weeks later", sum(size) people, round(100.0 * sum(kept) / sum(size), 1) pct_active_again,
           round(100.0 * sum(kept) filter (first_is_code) / sum(size) filter (first_is_code), 1) pct_if_code_first,
           round(100.0 * sum(kept) filter (not first_is_code) / sum(size) filter (not first_is_code), 1) pct_if_issue_first
           from ret group by k order by k""").show()
lap("done")
