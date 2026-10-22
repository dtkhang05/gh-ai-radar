# Account-age check for the star spike of 2023-03-08 (585,902 human stars that day, ~370k repos, most with 1-2 stars; see sample_day_anomalies.py).
# Groups: A = 200 random stars on repos with <= 2 stars that day (the campaign signature), B = 100 random stars on repos with > 2 stars that day,
# C = 100 random stars on the neighbouring normal sampled day 2023-03-15. Account creation dates come from GitHub GraphQL (100 logins per request,
# through the user's `gh` login); logins come from untrusted data, so they are validated by regex first. Age = days between account creation and the star.
# Output: data/derived/account_age_march2023.jsonl, then a summary table. Usage: python -I -X utf8 scripts/check_account_age_march2023.py
import duckdb, json, os, re, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
OUT = f"{ROOT}/data/derived/account_age_march2023.jsonl"
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
con.execute(f"""create table w as select repo, actor, ts, ts::date d from read_parquet('{ROOT}/data/parquet_sample/*.parquet')
  where type = 'WatchEvent' and actor not like '%[bot]' and ts::date in (date '2023-03-08', date '2023-03-15')""")
con.execute("""create table pick as
  with n as (select repo, d, count(*) c from w group by 1, 2),
       x as (select w.*, n.c, case when d = date '2023-03-15' then 'C normal day 03-15' when n.c <= 2 then 'A 03-08 repos <=2 stars' else 'B 03-08 repos >2 stars' end grp from w join n using (repo, d))
  select * from (select *, row_number() over (partition by grp order by hash(actor || repo || 'm3')) rn from x)
  where (grp like 'A%' and rn <= 200) or (grp like 'B%' and rn <= 100) or (grp like 'C%' and rn <= 100)""")
people = con.execute("select grp, repo, actor, ts from pick").fetchall()
safe = [p for p in people if LOGIN.fullmatch(p[2])]
print("accounts:", len(people), "valid logins:", len(safe))

def query(batch):
    parts = [f'u{i}: user(login: "{a}") {{ createdAt repositories(privacy: PUBLIC) {{ totalCount }} }}' for i, (_, _, a, _) in enumerate(batch)]
    return "query { rateLimit { cost remaining } " + " ".join(parts) + " }"

with open(OUT, "w", encoding="utf-8") as f:
    for s in range(0, len(safe), 100):
        batch = safe[s:s + 100]
        p = subprocess.run(["gh", "api", "graphql", "-f", "query=" + query(batch)], capture_output=True, text=True, encoding="utf-8")
        try: js = json.loads(p.stdout)
        except Exception: print("request failed:", p.stderr[:200]); sys.exit(1)
        data = js.get("data") or {}
        for i, (grp, repo, actor, ts) in enumerate(batch):
            u = data.get(f"u{i}")
            rec = dict(grp=grp, repo=repo, actor=actor, star_ts=str(ts))
            if u is None: rec["status"] = 404
            else:
                created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
                rec.update(status=200, age_days=(ts.replace(tzinfo=timezone.utc) - created).days, public_repos=u["repositories"]["totalCount"])
            f.write(json.dumps(rec) + "\n")
        print("batch", s // 100 + 1, (js.get("data") or {}).get("rateLimit"), flush=True)

con.execute(f"create view r as select * from read_json_auto('{OUT}')")
print(con.sql("""select grp, count(*) n, count(*) filter (where status = 404) not_found,
                        round(100.0 * count(*) filter (where status = 200 and age_days < 30) / nullif(count(*) filter (where status = 200), 0), 1) pct_new_30d,
                        round(100.0 * count(*) filter (where status = 200 and age_days < 1) / nullif(count(*) filter (where status = 200), 0), 1) pct_same_day,
                        median(age_days) filter (where status = 200) median_age,
                        round(100.0 * count(*) filter (where status = 200 and public_repos = 0) / nullif(count(*) filter (where status = 200), 0), 1) pct_no_repos
                 from r group by grp order by grp""").fetchall())
