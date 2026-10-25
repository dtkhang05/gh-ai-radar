# Account-age check for two minor anomalous sampled days (2024-06-12, 2024-11-13; see sample_minor_anomalies.py). Per day: the 10 repos with
# the largest excess stars over their median on the 6 nearest other sampled days, 20 random stargazers each, plus a control of 100 random
# stargazers of all other repos that day. Account creation dates come from GitHub GraphQL (100 logins per request, through the user's `gh`
# login); logins are untrusted, so validated by regex first. Repo names are printed here only; the docs do not name these repos.
# Output: data/derived/account_age_minor_days.jsonl. Usage: python -I -X utf8 scripts/check_account_age_minor_days.py
import duckdb, json, os, re, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
DAYS = ["2024-06-12", "2024-11-13"]
OUT = f"{ROOT}/data/derived/account_age_minor_days.jsonl"
TOP, PER, CTRL = 10, 20, 100

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
con.execute(f"""create table s as select repo, ts::date d, actor, ts from read_parquet('{ROOT}/data/parquet_sample/*.parquet')
  where type = 'WatchEvent' and actor not like '%[bot]'""")
con.execute("create table rd as select repo, d, count(*) st from s group by 1, 2")
con.execute("create table day as select distinct d from rd")
con.execute("create table pick (d date, grp varchar, repo varchar, actor varchar, ts timestamp)")
for d in DAYS:
    con.execute(f"""create or replace table top as
      with nb as (select d from day where d <> date '{d}' order by abs(d - date '{d}') limit 6),
      cand as (select repo, st from rd where d = date '{d}'),
      base as (select c.repo, median(coalesce(r.st, 0)) b from cand c cross join nb left join rd r on r.repo = c.repo and r.d = nb.d group by c.repo)
      select c.repo, c.st, c.st - base.b e from cand c join base using (repo) order by e desc limit {TOP}""")
    con.execute(f"""insert into pick
      select date '{d}', 'burst', repo, actor, ts from (
        select s.*, row_number() over (partition by s.repo order by hash(s.actor || 'm24')) rn
        from s join top using (repo) where s.d = date '{d}') where rn <= {PER}""")
    con.execute(f"""insert into pick
      select date '{d}', 'control', repo, actor, ts from s where d = date '{d}' and repo not in (select repo from top)
      order by hash(actor || repo || 'c24') limit {CTRL}""")
people = con.execute("select d, grp, repo, actor, ts from pick").fetchall()
safe = [p for p in people if LOGIN.fullmatch(p[3])]
print("accounts:", len(people), "valid:", len(safe))

def query(batch):
    parts = [f'u{i}: user(login: "{p[3]}") {{ createdAt repositories(privacy: PUBLIC) {{ totalCount }} }}' for i, p in enumerate(batch)]
    return "query { rateLimit { cost remaining } " + " ".join(parts) + " }"

with open(OUT, "w", encoding="utf-8") as f:
    for k in range(0, len(safe), 100):
        batch = safe[k:k + 100]
        p = subprocess.run(["gh", "api", "graphql", "-f", "query=" + query(batch)], capture_output=True, text=True, encoding="utf-8")
        try: js = json.loads(p.stdout)
        except Exception: print("request failed:", p.stderr[:200]); sys.exit(1)
        data = js.get("data") or {}
        for i, (d, grp, repo, actor, ts) in enumerate(batch):
            u = data.get(f"u{i}")
            rec = dict(d=str(d), grp=grp, repo=repo, actor=actor, star_ts=str(ts))
            if u is None: rec["status"] = 404
            else:
                created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
                rec.update(status=200, age_days=(ts.replace(tzinfo=timezone.utc) - created).days, public_repos=u["repositories"]["totalCount"])
            f.write(json.dumps(rec) + "\n")
        print("batch", k // 100 + 1, data.get("rateLimit"), flush=True)

con.execute(f"create view r as select * from read_json_auto('{OUT}')")
stats = """count(*) n, count(*) filter (where status = 404) not_found,
  round(100.0 * count(*) filter (where status = 200 and age_days < 30) / nullif(count(*) filter (where status = 200), 0), 1) pct_new_30d,
  round(100.0 * count(*) filter (where status = 200 and age_days < 1) / nullif(count(*) filter (where status = 200), 0), 1) pct_same_day,
  median(age_days) filter (where status = 200) median_age,
  round(100.0 * count(*) filter (where status = 200 and public_repos = 0) / nullif(count(*) filter (where status = 200), 0), 1) pct_no_repos"""
print("\nper day and group: d, grp, n, not_found, % <30d, % same day, median age, % no public repo")
for row in con.sql(f"select d, grp, {stats} from r group by 1, 2 order by 1, 2").fetchall(): print("  ", row)
print("\nper burst repo:")
for row in con.sql(f"select d, repo, {stats} from r where grp = 'burst' group by 1, 2 order by 1, pct_new_30d desc").fetchall(): print("  ", row)
