# Phase 5b: define the AI-repo universe from three signals, then measure recall on two hand-picked reference lists.
#   name   : whole-word keywords in the repo name (the old filter, same pattern as dbt macro ai_name_pattern)
#   topic  : the repo's GitHub topics contain one of TOPICS (fixed list below)
#   desc   : the repo description matches DESC_PATTERN
# Pool = repos with >= MIN_STARS stars in the window (2025-03-01..05-22) that are in top_repos_by_stars.parquet (min 98 stars) and
# were found by fetch_repo_metadata.py. Repos the API could not find (renamed/deleted/private) can only match by name.
# The rules are fixed BEFORE looking at list 2; list 1 was used to see which kinds of repos the name filter missed.
# Usage: python -I -X utf8 scripts/ai_repos_classify.py
# With RADAR_INCLUDE_LOW=1 the pool also contains the 30-99 star repos (repos_30_99.parquet, metadata from fetch_repo_metadata.py with
# RADAR_META_SRC/RADAR_META_OUT) and the result goes to ai_repo_universe_low.parquet; ai_repo_universe.parquet (the one dbt reads) is untouched.
import duckdb, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
D = f"{ROOT}/data/derived"
LOW = os.environ.get("RADAR_INCLUDE_LOW") == "1"
MIN_STARS = 30 if LOW else 100
SUFFIX = "_low" if LOW else ""
import importlib.util
_spec = importlib.util.spec_from_file_location("ai_rules", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_rules.py"))  # -I drops the script dir from sys.path
_rules = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_rules)
NAME_RE, TOPICS, DESC_RE = _rules.NAME_RE, _rules.TOPICS, _rules.DESC_RE

meta = {}
for l in open(f"{D}/repo_metadata.jsonl", encoding="utf-8"):
    r = json.loads(l); meta[r["repo"]] = r
if LOW:
    for l in open(f"{D}/repo_metadata_30_99.jsonl", encoding="utf-8"):
        r = json.loads(l); meta[r["repo"]] = r
con = duckdb.connect()
# The top-20k list reaches down to 98 stars, so it always uses 100 here; the 30-99 star pool is the second list (no repo is in both).
pool = con.execute(f"select repo, stars from read_parquet('{D}/top_repos_by_stars.parquet') where stars >= 100").fetchall()
if LOW:
    pool += con.execute(f"select repo, stars from read_parquet('{D}/repos_30_99.parquet')").fetchall()
rows = []
for repo, stars in pool:
    m = meta.get(repo) or {}
    by_name = bool(NAME_RE.search(repo.split("/")[1].lower()))
    by_topic = bool(TOPICS & set(m.get("topics") or []))
    by_desc = bool(DESC_RE.search(m.get("desc") or ""))
    rows.append(dict(repo=repo, stars=stars, found=bool(m.get("found")), by_name=by_name, by_topic=by_topic, by_desc=by_desc,
                     is_ai=by_name or by_topic or by_desc, descr=(m.get("desc") or "")[:140], topics=",".join((m.get("topics") or [])[:8])))
con.execute("create table u as select * from (values " + ",".join(["(?,?,?,?,?,?,?,?,?)"] * len(rows)) + ") t(repo,stars,found,by_name,by_topic,by_desc,is_ai,descr,topics)",
            [v for r in rows for v in (r["repo"], r["stars"], r["found"], r["by_name"], r["by_topic"], r["by_desc"], r["is_ai"], r["descr"], r["topics"])])
con.execute(f"copy (select * from u where is_ai) to '{D}/ai_repo_universe{SUFFIX}.parquet' (format parquet)")
print(f"pool (>= {MIN_STARS} stars, top-20k list): {len(rows)} | API found: {sum(r['found'] for r in rows)} | not found: {sum(not r['found'] for r in rows)}")
con.sql("select count(*) filter (is_ai) ai_total, count(*) filter (by_name) by_name, count(*) filter (by_topic) by_topic, count(*) filter (by_desc) by_desc, "
        "count(*) filter (is_ai and not by_name) added_by_metadata from u").show()

for fname in ("ai_reference_repos.txt", "ai_reference_repos_2.txt"):
    refs = [l.strip() for l in open(f"{ROOT}/scripts/{fname}", encoding="utf-8") if l.strip() and not l.startswith("#")]
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r) for r in refs)
    low = {r["repo"].lower(): r for r in rows}
    hit = [low.get(r.lower()) for r in refs]
    inpool = [h for h in hit if h]
    print(f"\n== {fname}: {len(refs)} listed, {len(inpool)} in pool (>= {MIN_STARS} stars in window, top-20k)")
    for label, key in (("name only (old filter)", "by_name"), ("topic only", "by_topic"), ("description only", "by_desc"), ("ANY signal (new)", "is_ai")):
        n = sum(h[key] for h in inpool); print(f"   recall {label:24s}: {n}/{len(inpool)} = {100*n/len(inpool):.0f}%")
    missed = [h["repo"] for h in inpool if not h["is_ai"]]
    print("   still missed:", missed)
    print("   not in pool:", [r for r, h in zip(refs, hit) if not h])
