# Sensitivity of the thin-account check on the 2023-2024 sample (sample_thin_stars.py fixed three choices: thin = <= 3 events in the sample,
# flag = >= 60% thin, >= 500 stars in the quarter). Here: grid over those three, on the sample-based AI universe with renamed repos merged.
# Prints, for each combination, how many repo-quarters are flagged and how many of the top-8 repos per quarter are flagged. Names are printed to
# the terminal only (do not copy them into tracked files). Usage: python -I -X utf8 scripts/sample_thin_sensitivity.py
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a).replace(os.sep, "/")
con = duckdb.connect()
con.execute(f"set memory_limit='4GB'; set threads=4; set temp_directory='{P('data', 'duck_tmp')}'; set max_temp_directory_size='20GB'")
con.execute(f"create view m as select repo, coalesce(canon, repo) canon, is_ai from read_parquet('{P('data','derived','ai_repo_universe_sample.parquet')}')")
con.execute(f"""create table st as
  select m.canon repo, w.actor, strftime(w.ts, '%Y') || '-Q' || quarter(w.ts) q
  from read_parquet('{P('data','parquet_sample','*.parquet')}') w join m on m.repo = w.repo
  where w.type = 'WatchEvent' and w.actor not like '%[bot]' and m.is_ai""")
con.execute(f"""create table ev as
  select actor, count(*) n from read_parquet('{P('data','parquet_sample','*.parquet')}')
  where actor in (select distinct actor from st) group by 1""")
con.execute("create table sa as select st.repo, st.q, st.actor, ev.n from st join ev using (actor)")
rows = []
for thin_n in (1, 2, 3, 5, 10):
    con.execute(f"""create or replace table rq as
      select repo, q, count(*) stars, count(*) filter (where n <= {thin_n}) thin from sa group by 1, 2""")
    overall = con.sql("select round(100.0 * sum(thin) / sum(stars), 1) from rq").fetchone()[0]
    for pct in (0.4, 0.5, 0.6, 0.7):
        for mins in (200, 500):
            r = con.sql(f"""select count(*) filter (where stars >= {mins}), count(*) filter (where stars >= {mins} and thin >= {pct} * stars) from rq""").fetchone()
            top = con.sql(f"""select count(*) filter (where thin >= {pct} * stars), count(*) from (
                select *, row_number() over (partition by q order by stars desc) rn from rq) where rn <= 8""").fetchone()
            rows.append((thin_n, overall, pct, mins, r[0], r[1], top[0], top[1]))
print("thin_n (<= events), overall thin %, min thin share, min stars, repo-quarters eligible, flagged, top-8 flagged, top-8 total")
for r in rows: print("  ", r)
con.execute("""create or replace table rq as select repo, q, count(*) stars, count(*) filter (where n <= 3) thin from sa group by 1, 2""")
print("\nflagged at the most lenient setting seen above (thin<=3, >=40%, >=200 stars), top 15 by stars (terminal only):")
for r in con.sql("select repo, q, stars, round(100.0 * thin / stars, 1) from rq where stars >= 200 and thin >= 0.4 * stars order by stars desc limit 15").fetchall(): print("  ", r)
