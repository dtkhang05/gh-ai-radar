# Phase 5b: list the most-starred repos in the window regardless of their name, so their GitHub topics/description can be fetched
# (fetch_repo_metadata.py). The name filter alone had 25% recall; this is the candidate pool for a topic-based definition.
# Usage: python -I -X utf8 scripts/top_repos_by_stars.py [N]   (default N = 20000)
import duckdb, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
PQ = f"{ROOT}/data/parquet"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
files = f"['{PQ}/2025-03-*.parquet', '{PQ}/2025-04-*.parquet', '{PQ}/2025-05-*.parquet']"
con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=3; set max_temp_directory_size='5GB'")
con.execute(f"set temp_directory='{ROOT}/data/duck_tmp'")
con.execute(f"""create table stars as
  select repo, count(*) stars from read_parquet({files})
  where type = 'WatchEvent' and ts >= '2025-03-01' and ts < '2025-05-23' and repo is not null group by 1""")
print("repos with any star:", con.sql("select count(*) from stars").fetchone()[0])
for t in (10, 30, 50, 100, 300):
    print(f"  >= {t} stars:", con.sql(f"select count(*) from stars where stars >= {t}").fetchone()[0])
con.execute(f"copy (select repo, stars from stars order by stars desc, repo limit {N}) to '{ROOT}/data/derived/top_repos_by_stars.parquet' (format parquet)")
print(f"top {N}: min stars =", con.sql(f"select min(stars) from (select stars from stars order by stars desc limit {N})").fetchone()[0])
