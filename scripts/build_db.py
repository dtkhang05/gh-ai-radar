# Phase 2: load hourly Parquet into DuckDB and print per-day sanity checks.
# Usage: python -I -X utf8 scripts/build_db.py
import duckdb, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = duckdb.connect(os.path.join(ROOT, "data", "radar.duckdb"))
# shared machine (other project runs Docker): cap resources so one query cannot exhaust RAM or disk
con.execute("set memory_limit='3GB'; set threads=4; set max_temp_directory_size='5GB'")
pq = os.path.join(ROOT, "data", "parquet", "*.parquet").replace("\\", "/")
# View, not table: Parquet is ~3.6x smaller than a DuckDB copy, and the data stays stored once.
con.execute(f"create or replace view raw_events as select * from read_parquet('{pq}')")
mf = os.path.join(ROOT, "data", "manifest.jsonl").replace("\\", "/")
con.execute(f"create or replace table raw_manifest as select hour::timestamp as hour, * exclude (hour, by_type) from read_json('{mf}', format='newline_delimited')")
print("events:", con.sql("select count(*) from raw_events").fetchone()[0])
print("manifest status:\n", con.sql("select status, count(*) n from raw_manifest group by 1"))
print("per-day (events, stars, forks, pushes, distinct hours with data):")
con.sql("""
  select ts::date d, count(*) events,
         count(*) filter (type='WatchEvent') stars,
         count(*) filter (type='ForkEvent') forks,
         count(*) filter (type='PushEvent') pushes,
         count(distinct date_trunc('hour', ts)) hrs
  from raw_events group by 1 order by 1""").show(max_rows=40)
print("duplicate event ids:", con.sql("select count(*) - count(distinct id) from raw_events").fetchone()[0])
