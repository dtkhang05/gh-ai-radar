# Account-age check for the late-2024 thin-account signal of the two flagged repos (same owner): stars on the sampled days 2024-12-11 and
# 2024-12-25. Repos come from the owner of RADAR_FLAGGED_REPO (all that owner's repos with stars on those days; names stay out of tracked files).
# Groups: F = up to 200 random stars on the owner's repos on those days, C = 100 random stars on other repos of the sample-based AI universe on the
# same days. Account creation dates come from GitHub GraphQL (100 logins per request, through the user's `gh` login); logins are untrusted, so
# validated by regex first. Age = days between account creation and the star. Also prints event counts of the F accounts across the whole sample.
# Output: data/derived/account_age_dec2024.jsonl. Usage: RADAR_FLAGGED_REPO=<owner/name> python -I -X utf8 scripts/check_account_age_dec2024.py
import duckdb, json, os, re, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
SRC = "parquet_window" if os.environ.get("RADAR_WINDOW") else "parquet_sample"   # window = continuous days, see ingest_window.py
DAYS = os.environ.get("RADAR_DAYS", "2024-12-11,2024-12-25").split(",")
assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in DAYS)
OUT = f"{ROOT}/data/derived/account_age_dec2024" + ("_window" if os.environ.get("RADAR_WINDOW") else "") + ".jsonl"
owner = os.environ["RADAR_FLAGGED_REPO"].split("/")[0]
if not LOGIN.fullmatch(owner): sys.exit("bad owner")

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
con.execute(f"create view m as select repo, coalesce(canon, repo) canon, is_ai from read_parquet('{ROOT}/data/derived/ai_repo_universe_sample.parquet')")
con.execute(f"""create table w as select repo, actor, ts from read_parquet('{ROOT}/data/{SRC}/*.parquet')
  where type = 'WatchEvent' and actor not like '%[bot]' and ts::date in ({', '.join(f"date '{d}'" for d in DAYS)})""")
con.execute(f"""create table pick as
  with x as (select w.*, case when split_part(w.repo, '/', 1) = '{owner}' or split_part(coalesce(m.canon, w.repo), '/', 1) = '{owner}' then 'F flagged owner'
                              when m.is_ai then 'C other AI repos' end grp
             from w left join m on m.repo = w.repo)
  select * from (select *, row_number() over (partition by grp order by hash(actor || repo || 'd24')) rn from x where grp is not null)
  where (grp like 'F%' and rn <= 200) or (grp like 'C%' and rn <= 100)""")
people = con.execute("select grp, repo, actor, ts from pick").fetchall()
safe = [p for p in people if LOGIN.fullmatch(p[2])]
print("accounts:", len(people), "valid:", len(safe), "| F stars available:", con.sql("select count(*) from w where split_part(repo, '/', 1) = '" + owner + "'").fetchone()[0])

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
            rec = dict(grp=grp, actor=actor, star_ts=str(ts))
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
