# Probe one day of GH Archive: load slim columns, count, rough AI filter by repo name, write Parquet.
# Usage: python -I -X utf8 scripts/probe_day.py <folder with YYYY-MM-DD-H.json.gz files> <output folder>
import duckdb, time, sys, os
raw, out = sys.argv[1], sys.argv[2]
con = duckdb.connect()
t = time.time()
con.execute(f"""
create table ev as
select id, type, created_at::timestamp as ts, actor.login as actor, repo.name as repo
from read_json('{raw}/*.json.gz', format='newline_delimited', ignore_errors=true,
  columns={{id:'VARCHAR', type:'VARCHAR', created_at:'VARCHAR',
           actor:'STRUCT(login VARCHAR)', repo:'STRUCT(name VARCHAR)'}})
""")
print(f"load+slim: {time.time()-t:.1f}s")
print("events:", con.sql("select count(*) from ev").fetchone()[0])
print("repos:", con.sql("select count(distinct repo) from ev").fetchone()[0])
print("actors:", con.sql("select count(distinct actor) from ev").fetchone()[0])
print(con.sql("select type, count(*) n from ev group by 1 order by 2 desc limit 8"))
# Rough: keyword match on repo name only. Misses AI repos with plain names, catches false positives.
kw = "llm|gpt|agent|rag|diffusion|transformer|langchain|ollama|llama|claude|openai|mcp|ai-|-ai|ml-|neural|embedding"
con.execute(f"create table ai as select * from ev where regexp_matches(lower(repo), '{kw}')")
print("AI-keyword events:", con.sql("select count(*) from ai").fetchone()[0],
      "repos:", con.sql("select count(distinct repo) from ai").fetchone()[0])
print(con.sql("select repo, count(*) stars from ai where type='WatchEvent' group by 1 order by 2 desc limit 10"))
t = time.time()
con.execute(f"copy ev to '{out}/ev.parquet' (format parquet)")
print(f"parquet write: {time.time()-t:.1f}s, size {os.path.getsize(out+'/ev.parquet')/1e6:.0f} MB")
