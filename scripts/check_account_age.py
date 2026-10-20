# Independent check of the flagged star spike (2025-04-14/15, see PLAN.md Phase 7): are the stargazers newly created accounts?
# The flagged repo is not named in this code: pass it as the environment variable RADAR_FLAGGED_REPO=owner/repo.
# Samples 25 stargazers from the spike days and 25 from normal days of the same repo, asks the public GitHub API
# (unauthenticated, 60 req/h) for created_at / public_repos / followers, and compares the two groups.
# Logins come from downloaded data (untrusted): only strings matching GitHub's login rules are put into a URL.
# Usage: python -I -X utf8 scripts/check_account_age.py                                   (flagged repo from RADAR_FLAGGED_REPO, spike vs normal)
#        python -I -X utf8 scripts/check_account_age.py <owner/repo> <first day> <last day>  (control: spike group only)
import duckdb, os, re, sys, json, time, statistics, urllib.request, urllib.error
from datetime import datetime, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
PQ, OUT = f"{ROOT}/data/parquet", f"{ROOT}/data/derived"
REPO, SPIKE_DAYS, N = os.environ.get("RADAR_FLAGGED_REPO", ""), ("2025-04-14", "2025-04-15"), 25
CONTROL = len(sys.argv) == 4  # control repo: sample only the busy days, compare against the flagged repo's saved result
if CONTROL:
    REPO, SPIKE_DAYS = sys.argv[1], (sys.argv[2], sys.argv[3])
elif not REPO:
    raise SystemExit("set RADAR_FLAGGED_REPO=owner/repo (the repo flagged by star_anomalies.py), or pass <owner/repo> <first day> <last day> for a control")
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", REPO) or not all(re.fullmatch(r"\d{4}-\d\d-\d\d", d) for d in SPIKE_DAYS):
    raise SystemExit("bad repo or date argument")
TAG = REPO.replace("/", "__") if CONTROL else "flagged_repo"  # build_dashboard.py reads account_sample_flagged_repo.jsonl
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")  # GitHub login rule; skips [bot] and anything odd
H = {"User-Agent": "gh-ai-radar/0.1 (personal learning project)", "Accept": "application/vnd.github+json"}

def api(path):
    try:
        with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=H), timeout=30) as r:
            return r.status, json.load(r), int(r.headers.get("X-RateLimit-Remaining", -1))
    except urllib.error.HTTPError as e:
        return e.code, None, int(e.headers.get("X-RateLimit-Remaining", -1))

status, rl, _ = api("/rate_limit")
core = rl["resources"]["core"] if status == 200 else None
print("rate limit:", core)
if not core or core["remaining"] < (1 if CONTROL else 2) * N + 5:  # control mode samples one group only
    raise SystemExit("not enough API quota left; try again after the reset time above")

con = duckdb.connect()
con.execute("set memory_limit='2GB'; set threads=2")
files = f"['{PQ}/2025-03-*.parquet', '{PQ}/2025-04-*.parquet', '{PQ}/2025-05-*.parquet']"
con.execute(f"""create table s as select actor, ts::date d from read_parquet({files})
  where repo = '{REPO}' and type = 'WatchEvent' and ts < '2025-05-23' and actor is not null""")
spike_in = f"date '{SPIKE_DAYS[0]}' and date '{SPIKE_DAYS[1]}'" if CONTROL else "(" + ",".join(f"date '{d}'" for d in SPIKE_DAYS) + ")"
spike_pred = f"d between {spike_in}" if CONTROL else f"d in {spike_in}"
spike_q = f"select 'spike' grp, actor, d from (select distinct actor, d from s where {spike_pred}) using sample reservoir({N} rows) repeatable (1)"
# normal group (flagged repo only) = every other day except the neighbouring spike days (11-16 Apr, 17 May)
normal_q = f"""select 'normal', actor, d from (select distinct actor, d from s where d not between date '2025-04-10' and date '2025-04-16'
               and d <> date '2025-05-17') using sample reservoir({N} rows) repeatable (2)"""
con.execute("create table pick as " + (f"({spike_q})" if CONTROL else f"({spike_q}) union all ({normal_q})"))
rows = []
for grp, login, d in con.sql("select grp, actor, d from pick").fetchall():
    if not LOGIN.match(login):
        rows.append(dict(grp=grp, login=login, status="skipped_invalid_login")); continue
    code, u, remaining = api(f"/users/{login}")
    rec = dict(grp=grp, login=login, star_day=str(d), status=code)
    if code == 200:
        created = datetime.strptime(u["created_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        rec.update(created=str(created), age_days=(d - created).days, public_repos=u["public_repos"], followers=u["followers"])
    rows.append(rec)
    if code in (403, 429) or remaining == 0:
        print("rate limited, stopping early"); break
    time.sleep(1)

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/account_sample_{TAG}.jsonl", "w", encoding="utf-8") as f:
    for r in rows: f.write(json.dumps(r) + "\n")

print(f"\n{REPO}  days {SPIKE_DAYS[0]}..{SPIKE_DAYS[-1]}")
print(f"{'group':8} {'asked':>5} {'ok':>4} {'deleted(404)':>12} {'med age (days)':>15} {'<30d old':>9} {'med repos':>10} {'0 repos':>8} {'med followers':>14}")
for grp in ("spike", "normal"):
    g = [r for r in rows if r["grp"] == grp]
    if not g: continue
    ok = [r for r in g if r["status"] == 200]
    if not ok: print(grp, "no data"); continue
    print(f"{grp:8} {len(g):>5} {len(ok):>4} {sum(r['status'] == 404 for r in g):>12} "
          f"{statistics.median(r['age_days'] for r in ok):>15.0f} "
          f"{sum(r['age_days'] < 30 for r in ok):>4}/{len(ok):<4} "
          f"{statistics.median(r['public_repos'] for r in ok):>10.0f} {sum(r['public_repos'] == 0 for r in ok):>8} "
          f"{statistics.median(r['followers'] for r in ok):>14.0f}")
