# Account-age check for the 2023-2024 sample: how old are the accounts that starred the biggest AI repos of each quarter?
# Groups: the top 3 AI repos of each quarter (by stars per sampled day, data/derived/sample_repo_quarters.parquet), 25 random stargazers each from
# that quarter's sampled days, plus one baseline group of 100 random stargazers of random AI repos. Account creation dates come from GitHub GraphQL
# (100 logins per request, through the user's `gh` login). Logins come from untrusted data, so they are validated by regex before they go into a
# query. Age = days between the account's creation and the star. Repo names are NOT printed for the flagged repos in the docs, only here.
# Output: data/derived/account_age_sample.jsonl, one line per sampled account. Usage: python -I -X utf8 scripts/check_account_age_sample.py
import duckdb, json, os, re, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
D = f"{ROOT}/data/derived"
OUT = f"{D}/account_age_sample.jsonl"
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
N = 25

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
con.execute(f"""create table top3 as
  select repo, q from (select repo, q, row_number() over (partition by q order by stars_per_day desc) rn
                       from read_parquet('{D}/sample_repo_quarters.parquet')) where rn <= 3""")
con.execute(f"""create table st as
  select repo, strftime(ts, '%Y') || '-Q' || quarter(ts) q, actor, ts
  from read_parquet('{ROOT}/data/parquet_sample/*.parquet') where type = 'WatchEvent' and actor not like '%[bot]'""")
con.execute(f"""create table pick as
  select * from (select t.repo, t.q, s.actor, s.ts, row_number() over (partition by t.repo, t.q order by hash(s.actor || 's7')) rn
                 from top3 t join st s using (repo, q)) where rn <= {N}""")
con.execute(f"""create table base as
  select 'baseline (random AI repos)' repo, 'all' q, actor, ts from (
    select s.actor, s.ts from st s where s.repo in (select repo from read_parquet('{D}/ai_repo_universe_low.parquet') where is_ai)
    order by hash(s.actor || s.repo || 's7b') limit 100)""")
people = con.execute("select repo, q, actor, ts from pick union all select repo, q, actor, ts from base").fetchall()
print("accounts to look up:", len(people))

def query(batch):
    parts = [f'u{i}: user(login: "{a}") {{ createdAt repositories(privacy: PUBLIC) {{ totalCount }} }}' for i, (_, _, a, _) in enumerate(batch)]
    return "query { rateLimit { cost remaining } " + " ".join(parts) + " }"

safe = [p for p in people if LOGIN.fullmatch(p[2])]
print("valid logins:", len(safe), "skipped:", len(people) - len(safe))
with open(OUT, "w", encoding="utf-8") as f:
    for s in range(0, len(safe), 100):
        batch = safe[s:s + 100]
        p = subprocess.run(["gh", "api", "graphql", "-f", "query=" + query(batch)], capture_output=True, text=True, encoding="utf-8")
        try: js = json.loads(p.stdout)
        except Exception: print("request failed:", p.stderr[:200]); sys.exit(1)
        data = js.get("data") or {}
        for i, (repo, q, actor, ts) in enumerate(batch):
            u = data.get(f"u{i}")
            rec = dict(repo=repo, q=q, actor=actor, star_ts=str(ts))
            if u is None: rec["status"] = 404
            else:
                created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
                rec.update(status=200, created=u["createdAt"], age_days=(ts.replace(tzinfo=timezone.utc) - created).days, public_repos=u["repositories"]["totalCount"])
            f.write(json.dumps(rec) + "\n")
        print("batch", s // 100 + 1, "cost", (js.get("data") or {}).get("rateLimit"), flush=True)
