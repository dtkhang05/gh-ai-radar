# Thin-account check on the 2023-2024 sample: which AI repos get their stars from accounts that do almost nothing else?
# Thin account = at most 3 events in the WHOLE sample (72 days, same cut-off as the 2025 analysis but over a sparser window, so thin shares are
# higher here than in 2025 and only comparable between repos inside this sample). A repo-quarter is flagged when >= 60% of its stargazers are
# thin and it has >= 500 stars in the quarter's sampled days. Usage: python -I -X utf8 scripts/sample_thin_stars.py
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a).replace(os.sep, "/")
con = duckdb.connect()
con.execute(f"set memory_limit='4GB'; set threads=4; set temp_directory='{P('data', 'duck_tmp')}'; set max_temp_directory_size='20GB'")
con.execute(f"create view u as select repo from read_parquet('{P('data','derived','ai_repo_universe.parquet')}') where is_ai")
con.execute(f"""create table st as
  select repo, actor, ts::date d, strftime(ts, '%Y') || '-Q' || quarter(ts) q
  from read_parquet('{P('data','parquet_sample','*.parquet')}')
  where type = 'WatchEvent' and actor not like '%[bot]' and repo in (select repo from u)""")
con.execute("create table actors as select distinct actor from st")
con.execute(f"""create table ev as
  select actor, count(*) n from read_parquet('{P('data','parquet_sample','*.parquet')}')
  where actor in (select actor from actors) group by 1""")
con.execute("""create table rq as
  select st.repo, st.q, count(*) stars, count(*) filter (where ev.n <= 3) thin
  from st join ev using (actor) group by 1, 2""")
con.execute("create table flagged as select *, round(100.0 * thin / stars, 1) thin_pct from rq where stars >= 500 and thin >= 0.6 * stars")
con.execute(f"copy rq to '{P('data','derived','sample_thin_quarters.parquet')}' (format parquet)")

print("AI-universe stargazers: thin share overall (stars-weighted):", con.sql("select round(100.0 * sum(thin) / sum(stars), 1) from rq").fetchone()[0], "%")
print("repo-quarters with >= 500 stars:", con.sql("select count(*) from rq where stars >= 500").fetchone()[0], "| flagged (>= 60% thin):", con.sql("select count(*) from flagged").fetchone()[0])
print("\nflagged repo-quarters (repo, quarter, stars, thin %):")
for r in con.sql("select repo, q, stars, thin_pct from flagged order by stars desc limit 25").fetchall():
    print("  ", r)
print("\nhow many of the top-8 repos per quarter (by stars) are flagged:")
print("  ", con.sql("""select count(*) filter (where f.repo is not null), count(*) from (
        select repo, q, row_number() over (partition by q order by stars desc) rn from rq) t
        left join flagged f using (repo, q) where t.rn <= 8""").fetchone())
print("\nthin share of the 5 biggest repos per quarter:")
for r in con.sql("""select q, repo, stars, round(100.0 * thin / stars, 1) from (select *, row_number() over (partition by q order by stars desc) rn from rq) where rn <= 5 order by q, stars desc""").fetchall():
    print("  ", r)
