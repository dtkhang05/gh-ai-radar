# End-to-end recall of the AI-repo universe: of the hand-picked reference AI repos that were active in the window with >= MIN_STARS
# stars, how many are in the dbt model int_ai_repo_candidates? Reports misses so the definition can be judged honestly.
# Window and star threshold match dbt_radar/dbt_project.yml. (ai_repos_classify.py reports the same recall per signal, before dbt.)
# Usage: python -I -X utf8 scripts/ai_repos_recall.py [reference_list.txt]   (default: ai_reference_repos.txt; second list: ai_reference_repos_2.txt)
import duckdb, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
PQ = f"{ROOT}/data/parquet"
files = f"['{PQ}/2025-03-*.parquet', '{PQ}/2025-04-*.parquet', '{PQ}/2025-05-*.parquet']"
START, END, MIN_STARS = "2025-03-01", "2025-05-23", 100

refs = [l.strip() for l in open(f"{ROOT}/scripts/" + (sys.argv[1] if len(sys.argv) > 1 else "ai_reference_repos.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")]
assert all(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r) for r in refs), "bad line in reference list"

con = duckdb.connect()
con.execute("set memory_limit='3GB'; set threads=4")
con.execute("create table refs(repo varchar)")
con.executemany("insert into refs values (?)", [(r.lower(),) for r in refs])
con.execute(f"""create table activity as
  select lower(repo) repo, count(*) events, count(*) filter (type = 'WatchEvent') stars
  from read_parquet({files}) where ts >= '{START}' and ts < '{END}' and lower(repo) in (select repo from refs) group by 1""")
con.execute(f"attach '{ROOT}/data/radar_dbt.duckdb' as dbt (read_only)")
con.execute("create table cand as select lower(repo) repo from dbt.main.int_ai_repo_candidates")
con.execute(f"""create table res as
  select r.repo, coalesce(a.events, 0) events, coalesce(a.stars, 0) stars,
         case when a.repo is null then 'absent (renamed or no events)'
              when a.stars < {MIN_STARS} then 'below star threshold'
              when c.repo is not null then 'IN filter' else 'MISSED' end status
  from refs r left join activity a using (repo) left join cand c using (repo)""")
print("reference repos:", len(refs))
con.sql("select status, count(*) n from res group by 1 order by 2 desc").show()
eligible, hit = con.sql("select count(*) filter (status in ('IN filter','MISSED')), count(*) filter (status = 'IN filter') from res").fetchone()
print(f"RECALL on reference repos that were active with >= {MIN_STARS} stars: {hit}/{eligible} = {100*hit/eligible:.0f}%")
print("\nMISSED (active, enough stars, but not in the filter):")
con.sql("select repo, stars from res where status = 'MISSED' order by stars desc").show(max_rows=60)
print("Absent from the data in this window (not counted):", [r[0] for r in con.sql("select repo from res where status like 'absent%' order by repo").fetchall()])
