# Look inside the three minor anomalous sampled days (ratio 1.25-1.5 in sample_day_anomalies.py): is the excess one campaign (a few repos,
# many 1-2 star repos) or ordinary growth? For each day: total stars vs the median of the 6 nearest other sampled days, the share of the
# excess carried by the top 10 repos, the number of repos with 1-2 stars, and the top 5 repos. The flagged repos are masked.
# Usage: RADAR_FLAGGED_REPO=owner/name python -I -X utf8 scripts/sample_minor_anomalies.py
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "data", "parquet_sample", "*.parquet").replace(os.sep, "/")
DAYS = ["2023-03-22", "2024-06-12", "2024-11-13"]
OWNER = os.environ.get("RADAR_FLAGGED_REPO", "none/none").split("/")[0]

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
con.execute(f"""create table s as
  select repo, ts::date d, actor from read_parquet('{SAMPLE}')
  where type = 'WatchEvent' and actor not like '%[bot]'""")
con.execute("create table rd as select repo, d, count(*) st from s group by 1, 2")
con.execute("create table day as select d, sum(st) tot, count(*) repos, count(*) filter (where st <= 2) small from rd group by d")
for d in DAYS:
    print("==", d)
    ref = con.execute(f"""select median(tot), median(repos), median(small) from
      (select * from day where d <> date '{d}' order by abs(d - date '{d}') limit 6)""").fetchone()
    cur = con.execute(f"select tot, repos, small from day where d = date '{d}'").fetchone()
    print(f"   stars {cur[0]} vs neighbours {ref[0]:.0f} ({cur[0] / ref[0]:.2f}x) | repos {cur[1]} vs {ref[1]:.0f} | repos with 1-2 stars {cur[2]} vs {ref[2]:.0f}")
    # per-repo excess = stars that day minus the repo's median over the 6 nearest other days (0 when absent)
    rows = con.execute(f"""
      with nb as (select d from day where d <> date '{d}' order by abs(d - date '{d}') limit 6),
      cand as (select repo, st from rd where d = date '{d}'),
      base as (select c.repo, median(coalesce(r.st, 0)) b
               from cand c cross join nb left join rd r on r.repo = c.repo and r.d = nb.d group by c.repo)
      select c.repo, c.st, round(c.st - base.b, 1) e from cand c join base using (repo) order by e desc limit 10""").fetchall()
    tot_ex = cur[0] - ref[0]
    top = sum(r[2] for r in rows)
    print(f"   excess over neighbours {tot_ex:.0f} stars; top 10 repos carry {top:.0f} ({100 * top / tot_ex:.0f}% of it)")
    for r in rows[:5]:
        name = "Repo X" if r[0].split("/")[0] == OWNER else r[0]
        print("     ", name, r[1], r[2])
