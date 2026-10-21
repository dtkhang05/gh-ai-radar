# Phase 5b: fetch description, topics, language and fork/archived flags for the repos in data/derived/top_repos_by_stars.parquet
# through GitHub's GraphQL API (100 repos per request, so 20,000 repos cost ~200 requests) using the user's `gh` login.
# Resumable: repos already in the output file are skipped. Names come from untrusted data, so they are validated by regex before
# they go into a query. Rate-limit guard: stops when fewer than 200 points remain.
# Usage: python -I -X utf8 scripts/fetch_repo_metadata.py [max_batches]
import duckdb, json, os, re, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
# Env overrides let the same script fetch a second pool (repos with 30-99 stars) into its own file without touching the first one.
SRC = os.environ.get("RADAR_META_SRC", f"{ROOT}/data/derived/top_repos_by_stars.parquet")
OUT = os.environ.get("RADAR_META_OUT", f"{ROOT}/data/derived/repo_metadata.jsonl")
MAX_BATCHES = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
GH = "gh"

repos = [r[0] for r in duckdb.connect().execute(f"select repo from read_parquet('{SRC}') order by stars desc, repo").fetchall()]
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding="utf-8"):
        try: done.add(json.loads(l)["repo"])
        except Exception: pass
todo = [r for r in repos if r not in done and NAME.fullmatch(r)]
print(f"{len(repos)} repos listed, {len(done)} done, {len(todo)} to fetch", flush=True)

FIELDS = "nameWithOwner description stargazerCount isArchived isFork primaryLanguage{name} repositoryTopics(first:20){nodes{topic{name}}}"
def query(batch):
    parts = []
    for i, r in enumerate(batch):
        o, n = r.split("/")
        parts.append(f'r{i}: repository(owner: "{o}", name: "{n}") {{ {FIELDS} }}')
    return "query { rateLimit { cost remaining resetAt } " + " ".join(parts) + " }"

n_batches = 0
with open(OUT, "a", encoding="utf-8") as f:
    for s in range(0, len(todo), 100):
        if n_batches >= MAX_BATCHES: break
        batch = todo[s:s + 100]
        for attempt in range(4):
            p = subprocess.run([GH, "api", "graphql", "-f", "query=" + query(batch)], capture_output=True, text=True, encoding="utf-8")
            try: js = json.loads(p.stdout); break
            except Exception: time.sleep(5 * (attempt + 1)); js = None
        if js is None:
            print("request failed:", p.stderr[:300]); break
        data = js.get("data") or {}
        for i, r in enumerate(batch):
            x = data.get(f"r{i}")
            if x is None:
                rec = dict(repo=r, found=False)
            else:
                rec = dict(repo=r, found=True, name=x["nameWithOwner"], desc=x["description"], stars_total=x["stargazerCount"],
                           archived=x["isArchived"], fork=x["isFork"], lang=(x["primaryLanguage"] or {}).get("name"),
                           topics=[t["topic"]["name"] for t in x["repositoryTopics"]["nodes"]])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush(); n_batches += 1
        rl = data.get("rateLimit") or {}
        if n_batches % 10 == 1: print(f"batch {n_batches}: cost {rl.get('cost')}, remaining {rl.get('remaining')}", flush=True)
        if rl.get("remaining", 5000) < 200: print("rate limit low, stopping; resumes at", rl.get("resetAt")); break
print("done batches:", n_batches)
