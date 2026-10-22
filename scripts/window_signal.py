# Day-by-day view of the flagged owner's repos in the continuous window data/parquet_window/ (see ingest_window.py): human stars per day, share from
# thin accounts (<= 3 events in the whole window), and the same for the other AI repos of the sample-based universe as a control. Purpose: find the
# day the late-2024 thin-account signal begins. The owner comes from RADAR_FLAGGED_REPO and is never printed in a way that reaches tracked files.
# Usage: RADAR_FLAGGED_REPO=<owner/name> python -I -X utf8 scripts/window_signal.py
import os, re
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
owner = os.environ["RADAR_FLAGGED_REPO"].split("/")[0]
assert re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner)
W = f"{ROOT}/data/parquet_window/*.parquet"
con = duckdb.connect()
con.execute(f"set memory_limit='4GB'; set threads=4; set temp_directory='{ROOT}/data/duck_tmp'; set max_temp_directory_size='20GB'")
con.execute(f"create view m as select repo, coalesce(canon, repo) canon, is_ai from read_parquet('{ROOT}/data/derived/ai_repo_universe_sample.parquet')")
con.execute(f"""create table st as
  select w.ts::date d, w.actor, case when split_part(w.repo, '/', 1) = '{owner}' then 'X' when m.is_ai then 'AI' end grp
  from read_parquet('{W}') w left join m on m.repo = w.repo
  where w.type = 'WatchEvent' and w.actor not like '%[bot]'""")
con.execute("delete from st where grp is null")
con.execute(f"create table ev as select actor, count(*) n from read_parquet('{W}') where actor in (select distinct actor from st) group by 1")
con.execute("create table j as select st.*, ev.n from st join ev using (actor)")
print("days in window:", con.sql(f"select count(distinct ts::date) from read_parquet('{W}')").fetchone()[0])
print("date, X stars, X thin %, X stars from accounts with 1 event, AI-control stars, control thin %")
for r in con.sql("""select d, count(*) filter (where grp='X') xs,
    round(100.0 * count(*) filter (where grp='X' and n <= 3) / nullif(count(*) filter (where grp='X'), 0), 1) xthin,
    count(*) filter (where grp='X' and n = 1) x1,
    count(*) filter (where grp='AI') cs,
    round(100.0 * count(*) filter (where grp='AI' and n <= 3) / nullif(count(*) filter (where grp='AI'), 0), 1) cthin
  from j group by d order by d""").fetchall():
    print("  ", r)
