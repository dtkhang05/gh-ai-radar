# Stricter "wave" measure on the 2023-2024 sample: a wave = an AI repo-quarter with >= MIN_RATE stars per sampled day AND >= RATIO x the repo's
# previous-quarter rate (a repo absent in the previous quarter counts as ratio infinity). Reports waves per quarter, the share of the quarter's AI
# stars they carry, and whether each wave repo was still above half its wave level 2 quarters later. Input: sample_repo_quarters_canon.parquet
# (run sample_waves.py with RADAR_UNIVERSE_MODE=sample first). Flagged repos are masked via RADAR_FLAGGED_REPO.
# Usage: RADAR_FLAGGED_REPO=<owner/name> python -I -X utf8 scripts/sample_waves_strict.py
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RQ = os.path.join(ROOT, "data", "derived", "sample_repo_quarters_canon.parquet").replace(os.sep, "/")
MIN_RATE = float(os.environ.get("RADAR_WAVE_RATE", "100"))
RATIO = float(os.environ.get("RADAR_WAVE_RATIO", "3"))
flagged = os.environ.get("RADAR_FLAGGED_REPO", "")

con = duckdb.connect()
con.execute(f"create table rq as select * from read_parquet('{RQ}')")
con.execute("""create table qs as select q, row_number() over (order by q) qi from (select distinct q from rq)""")
con.execute("""create table rqi as select r.repo, r.q, qs.qi, r.stars_per_day rate from rq r join qs using (q)""")
con.execute("""create table x as
  select c.repo, c.q, c.qi, c.rate, coalesce(p.rate, 0) prev, l.rate later
  from rqi c left join rqi p on p.repo = c.repo and p.qi = c.qi - 1 left join rqi l on l.repo = c.repo and l.qi = c.qi + 2""")
con.execute(f"""create table wave as select *, rate / nullif(prev, 0) ratio from x
  where rate >= {MIN_RATE} and (prev = 0 or rate >= {RATIO} * prev) and qi > 1""")
print(f"waves: >= {MIN_RATE:.0f} stars/day and >= {RATIO}x previous quarter (first quarter excluded: no previous quarter)")
print("   quarter, waves, share of quarter AI stars %, still >= 50% of wave level 2 quarters later (of those with data)")
for r in con.sql("""select w.q, count(*), round(100.0 * sum(w.rate) / (select sum(stars_per_day) from rq where q = w.q), 1),
                           count(*) filter (where later >= 0.5 * rate) || ' / ' || count(*) filter (where later is not null or qi + 2 <= (select max(qi) from qs))
                    from wave w group by w.q order by w.q""").fetchall():
    print("  ", r)
print("\ntop 3 waves per quarter by rate (flagged masked):")
for (q,) in con.sql("select q from qs order by q").fetchall():
    rows = con.execute("select case when repo = ? then 'Repo X' else repo end, round(rate), round(prev), round(ratio, 1) from wave where q = ? order by rate desc limit 3", [flagged, q]).fetchall()
    if rows: print("  ", q, rows)
