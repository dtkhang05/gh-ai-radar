# Find sampled days whose total human stars are far above their neighbours (mass-starring campaigns such as 2023-03-08) and recompute the
# quarterly AI share without them. Uses the sample-based universe (ai_repo_universe_sample.parquet, names merged to the current name).
# A day is flagged when its stars are > RATIO x the median of the 6 nearest OTHER sampled days (same idea as dq_sample.py, on stars).
# Usage: python -I -X utf8 scripts/sample_day_anomalies.py
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "data", "parquet_sample", "*.parquet").replace(os.sep, "/")
UNIVERSE = os.path.join(ROOT, "data", "derived", "ai_repo_universe_sample.parquet").replace(os.sep, "/")
RATIO = float(os.environ.get("RADAR_DAY_RATIO", "1.5"))

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
con.execute(f"create view m as select repo, coalesce(canon, repo) canon, is_ai from read_parquet('{UNIVERSE}')")
con.execute("create view u as select distinct canon repo from m where is_ai")
con.execute(f"""create table s as
  select coalesce(m.canon, w.repo) repo, w.ts::date d, count(*) st
  from read_parquet('{SAMPLE}') w left join m on m.repo = w.repo
  where w.type = 'WatchEvent' and w.actor not like '%[bot]' group by 1, 2""")
con.execute("""create table day as
  select d, sum(st) tot, sum(st) filter (where repo in (select repo from u)) ai, count(*) repos,
         strftime(d, '%Y') || '-Q' || quarter(d) q
  from s group by d""")
# median of the 6 nearest other sampled days by calendar distance
con.execute("""create table flag as
  select a.d, a.q, a.tot, a.ai, a.repos,
         (select median(tot) from (select b.tot from day b where b.d <> a.d order by abs(b.d - a.d) limit 6)) nb_ref
  from day a""")
con.execute(f"alter table flag add column hit boolean; update flag set hit = tot > {RATIO} * nb_ref")
print(f"flagged days (stars > {RATIO} x median of 6 nearest other sample days):")
for r in con.sql("select d, tot, round(nb_ref) nb_ref, round(tot / nb_ref, 2) ratio, repos, round(100.0 * ai / tot, 1) ai_pct from flag where hit order by d").fetchall():
    print("  ", r)
print("days below 0.7 x nb_ref (possible gaps):",
      con.sql("select d, tot, round(nb_ref) from flag where tot < 0.7 * nb_ref order by d").fetchall())
print("\nquarterly AI share, all days vs without flagged days (humans-only stars)")
print("   quarter, days, flagged, share all %, share without flagged %")
for r in con.sql("""select q, count(*), count(*) filter (where hit),
                           round(100.0 * sum(ai) / sum(tot), 2),
                           round(100.0 * sum(ai) filter (where not hit) / sum(tot) filter (where not hit), 2)
                    from flag group by q order by q""").fetchall():
    print("  ", r)
# For each flagged day: how concentrated is the excess? Repos with exactly 1-2 stars that day are the campaign signature.
for (d,) in con.sql("select d from flag where hit order by d").fetchall():
    r = con.execute("""select count(*) filter (where st <= 2), count(*) filter (where st > 2), sum(st) filter (where st <= 2)
                       from s where d = ?""", [d]).fetchone()
    print(f"   {d}: repos with <=2 stars {r[0]} (stars {r[2]}), repos with >2 stars {r[1]}")
