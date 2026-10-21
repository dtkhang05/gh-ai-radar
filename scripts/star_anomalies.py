# Insight 1 (exploratory): which AI repos had abnormal star spikes, and were the spike's stargazers "thin" accounts?
# Window 2025-03-01 .. 2025-05-22 (verified complete). Candidate repos: keyword-matched, >=10 stars (see ai_repos_probe.py).
# A spike is only a SUSPICION signal: viral posts also cause spikes. "Thin" = few events anywhere in the window.
# v2: repos need >=7 days with stars before the spike (else a launch day counts as a "spike"), the repo's normal-day
#     thin share needs >=30 stargazers to be trusted, and thresholds are swept to see which repos stay flagged.
# Usage: python -I -X utf8 scripts/star_anomalies.py
import duckdb, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
PQ, OUT = f"{ROOT}/data/parquet", f"{ROOT}/data/derived"
# RADAR_UNIVERSE (default ai_repo_universe.parquet) and RADAR_OUT_SUFFIX let the same analysis run on another repo set (e.g. the 30-star
# universe, ai_repo_universe_low.parquet) without overwriting the files the dashboard reads.
UNIVERSE = os.environ.get("RADAR_UNIVERSE", "ai_repo_universe.parquet")
SUFFIX = os.environ.get("RADAR_OUT_SUFFIX", "")
files = f"['{PQ}/2025-03-*.parquet', '{PQ}/2025-04-*.parquet', '{PQ}/2025-05-*.parquet']"
END = "2025-05-23"  # exclusive; data after 2025-05-23 16:00 UTC is incomplete
THIN_MAX = 3        # thin: <=3 events in the window
MIN_HIST_DAYS = 7   # days with >=1 star in the prior 14 days
MIN_NORMAL_N = 30   # stargazers on normal days needed to trust a repo's normal thin share
JUMP, JUMP_MIN_N = 0.30, 100  # "suspicious": thin share jumps >=0.30 above normal, on a spike day with >=100 stars
GRID = [(m, x) for m in (30, 50, 100) for x in (3, 5, 10)]  # (min stars/day, multiple of baseline)
MAIN = (50, 5)

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4; set max_temp_directory_size='5GB'")
con.execute(f"set temp_directory='{ROOT}/data/duck_tmp'")
t = time.time()
def lap(msg): print(f"[{time.time()-t:5.0f}s] {msg}", flush=True)

con.execute(f"create table cand as select repo from read_parquet('{OUT}/{UNIVERSE}')")
con.execute(f"""create table stars as
  select repo, ts::date d, actor from read_parquet({files})
  where type = 'WatchEvent' and ts < '{END}' and actor is not null and repo in (select repo from cand)""")
lap(f"stars on candidate repos: {con.sql('select count(*) from stars').fetchone()[0]:,}")

con.execute("""create table daily as
  with cal as (select repo, unnest(generate_series(date '2025-03-01', date '2025-05-22', interval 1 day))::date d from cand),
  j as (select c.repo, c.d, coalesce(n.n, 0) n from cal c left join (select repo, d, count(*) n from stars group by 1, 2) n using (repo, d))
  select *, median(n) over w base, count(*) over w nb, sum((n > 0)::int) over w hist_days
  from j window w as (partition by repo order by d rows between 14 preceding and 1 preceding)""")

con.execute("create table actors as select distinct actor from stars")
con.execute(f"""create table actor_ev as
  select actor, count(*) ev from read_parquet({files})
  where ts < '{END}' and actor in (select actor from actors) group by 1""")
con.execute(f"""create table repo_day_thin as
  select s.repo, s.d, count(*) n, avg((e.ev <= {THIN_MAX})::int) thin_share
  from stars s join actor_ev e using (actor) group by 1, 2""")
lap(f"stargazers: {con.sql('select count(*) from actor_ev').fetchone()[0]:,}")

def spikes(min_n, x):
    return f"""select d.repo, d.d, d.n, round(d.base, 1) base, round(d.n / greatest(d.base, 1), 1) x_base,
        round(t.thin_share, 3) thin_spike, nrm.n_normal, round(nrm.thin_normal, 3) thin_normal,
        round(t.thin_share - nrm.thin_normal, 3) jump
      from daily d join repo_day_thin t using (repo, d)
      left join (select r.repo, sum(r.n) n_normal, sum(r.thin_share * r.n) / sum(r.n) thin_normal
                 from repo_day_thin r join daily d2 using (repo, d)
                 where not (d2.nb >= 7 and d2.hist_days >= {MIN_HIST_DAYS} and d2.n >= {min_n} and d2.n >= {x} * greatest(d2.base, 1))
                 group by 1 having sum(r.n) >= {MIN_NORMAL_N}) nrm using (repo)
      where d.nb >= 7 and d.hist_days >= {MIN_HIST_DAYS} and d.n >= {min_n} and d.n >= {x} * greatest(d.base, 1)"""

print("\nSensitivity grid (repo-days flagged as spikes / suspicious = jump>=%.2f, n>=%d):" % (JUMP, JUMP_MIN_N))
rows, seen = [], {}
for m, x in GRID:
    con.execute(f"create or replace temp table sp as {spikes(m, x)}")
    n_sp, n_rp, med_s, med_n = con.sql("select count(*), count(distinct repo), round(median(thin_spike),3), round(median(thin_normal),3) from sp").fetchone()
    sus = [r[0] for r in con.sql(f"select distinct repo from sp where n >= {JUMP_MIN_N} and jump >= {JUMP}").fetchall()]
    for r in sus: seen[r] = seen.get(r, 0) + 1
    rows.append((m, x, n_sp, n_rp, med_s, med_n, len(sus)))
    if (m, x) == MAIN:
        con.execute(f"copy sp to '{OUT}/star_spikes{SUFFIX}.parquet' (format parquet)")
        con.execute("create or replace table sp_main as select * from sp")
print(f"{'min/day':>8} {'xBase':>6} {'spike-days':>11} {'repos':>6} {'thin@spike':>11} {'thin@normal':>12} {'suspicious':>11}")
for r in rows: print(f"{r[0]:>8} {r[1]:>6} {r[2]:>11} {r[3]:>6} {r[4]:>11} {r[5]:>12} {r[6]:>11}")

print(f"\nSuspicious repos by number of configs (of {len(GRID)}) that flag them:")
for r, c in sorted(seen.items(), key=lambda kv: -kv[1])[:15]: print(f"  {c}/{len(GRID)}  {r}")

print("\nMain config (min 50/day, 5x) top 15 spikes by thin-share jump (n>=100):")
con.sql(f"select * from sp_main where n >= {JUMP_MIN_N} and jump is not null order by jump desc limit 15").show(max_rows=20)
print("Main config top 10 spikes by stars (sanity: should be real launches):")
con.sql("select * from sp_main order by n desc limit 10").show(max_rows=12)
lap("done")
