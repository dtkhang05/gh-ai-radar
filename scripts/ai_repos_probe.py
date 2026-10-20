# Phase 5 probe: find AI repos by whole-word keywords in the repo name, then eyeball precision.
# Window = 2025-03-01 .. 2025-05-22 (range verified as complete by dq_hourly.py).
# Light on resources: memory/threads/temp-disk capped, filter by repo name BEFORE grouping, no big in-memory table.
# Usage: python -I -X utf8 scripts/ai_repos_probe.py
import duckdb, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PQ = os.path.join(ROOT, "data", "parquet").replace("\\", "/")
con = duckdb.connect()  # in-memory: do not touch radar.duckdb
con.execute("set memory_limit='4GB'; set threads=2; set max_temp_directory_size='5GB'")
con.execute(f"set temp_directory='{ROOT}/data/duck_tmp'".replace("\\", "/"))

# Tokens must match as whole words (split on non-alphanumerics); long distinctive names also match as substrings.
TOKENS = "llm|llms|gpt|agent|agents|rag|diffusion|transformers|embedding|embeddings|mcp|genai|chatbot|copilot|ai|ml"
SUBSTR = "langchain|llamaindex|ollama|llama|openai|chatgpt|anthropic|claude|huggingface|stable-diffusion|deepseek|langgraph|autogen|crewai"
pat = rf"(^|[^a-z0-9])({TOKENS})([^a-z0-9]|$)|({SUBSTR})"
files = f"['{PQ}/2025-03-*.parquet', '{PQ}/2025-04-*.parquet', '{PQ}/2025-05-*.parquet']"
con.execute(f"""
create temp table cand as
select repo, count(*) events, count(*) filter (type = 'WatchEvent') stars
from read_parquet({files})
where ts < '2025-05-23' and repo is not null
  and regexp_matches(split_part(lower(repo), '/', 2), '{pat}')
group by 1""")
print("keyword-matched repos:", con.sql("select count(*) from cand").fetchone()[0],
      "| with >=10 stars:", con.sql("select count(*) from cand where stars >= 10").fetchone()[0])
print("\nTop 25 by stars:")
con.sql("select repo, stars, events from cand order by stars desc limit 25").show(max_rows=30)
print("Random sample of 40 repos with >=10 stars (judge by eye: AI or not?):")
# Filter in a subquery first: USING SAMPLE runs before WHERE in the same SELECT (that returned 0 rows).
con.sql("select * from (select repo, stars from cand where stars >= 10) using sample reservoir(40 rows) repeatable (42)").show(max_rows=45)
os.makedirs(f"{ROOT}/data/derived", exist_ok=True)
con.execute(f"copy cand to '{ROOT}/data/derived/ai_repo_candidates.parquet' (format parquet)".replace("\\", "/"))
