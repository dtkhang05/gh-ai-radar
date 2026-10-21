# AI-repo universe built from the 2023-2024 sample itself (not from 2025 stars): every repo with >= 30 star events in the 72 sample days
# (data/derived/sample_pool_30.parquet), metadata fetched with fetch_repo_metadata.py (RADAR_META_SRC/OUT -> repo_metadata_sample.jsonl).
# Why: the 2025-based universe (ai_repo_universe.parquet) misses repos that were popular in 2023-2024 but had < 30 stars in 03-05/2025, and it
# cannot follow repos that changed owner or name, because events carry the name at event time while the universe uses the 2025 name.
# GitHub's API resolves an OLD name to the repo's CURRENT name (nameWithOwner), so renamed repos are detected and their histories merged under
# `canon` (current name). Repos the API cannot find (deleted, private, renamed and the old name reused) only match by name and keep their own name.
# Rules are the same as the 2025 universe (scripts/ai_rules.py). Also measures recall on the three reference lists, and compares reference list 3
# with the old 2025-based universe (ai_repo_universe_low.parquet, exact name).
# Usage: python -I -X utf8 scripts/ai_repos_classify_sample.py
import duckdb, json, os, re
import importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
D = f"{ROOT}/data/derived"
_spec = importlib.util.spec_from_file_location("ai_rules", f"{ROOT}/scripts/ai_rules.py")  # -I drops the script dir from sys.path
_rules = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_rules)
NAME_RE, TOPICS, DESC_RE = _rules.NAME_RE, _rules.TOPICS, _rules.DESC_RE

meta = {}
for l in open(f"{D}/repo_metadata_sample.jsonl", encoding="utf-8"):
    r = json.loads(l); meta[r["repo"]] = r
con = duckdb.connect()
pool = [r for r in con.execute(f"select repo, stars from read_parquet('{D}/sample_pool_30.parquet')").fetchall() if r[0] in meta]
rows = []
for repo, stars in pool:
    m = meta[repo]; found = bool(m.get("found")); cur = m.get("name") if found else None
    by_name = bool(NAME_RE.search(repo.split("/")[1].lower())) or bool(cur and NAME_RE.search(cur.split("/")[1].lower()))
    by_topic = bool(TOPICS & set(m.get("topics") or []))
    by_desc = bool(DESC_RE.search(m.get("desc") or ""))
    rows.append((repo, stars, found, cur or repo, bool(cur) and cur.lower() != repo.lower(), by_name, by_topic, by_desc, by_name or by_topic or by_desc,
                 (m.get("desc") or "")[:140], ",".join((m.get("topics") or [])[:8])))
con.execute("create table u(repo varchar, stars_sample integer, found boolean, canon varchar, renamed boolean, by_name boolean, by_topic boolean, by_desc boolean, is_ai boolean, descr varchar, topics varchar)")
con.executemany("insert into u values (?,?,?,?,?,?,?,?,?,?,?)", rows)
con.execute(f"copy u to '{D}/ai_repo_universe_sample.parquet' (format parquet)")
print(f"pool with metadata: {len(rows)} of {len(pool)} listed | found: {sum(r[2] for r in rows)} | renamed/moved: {sum(r[4] for r in rows)}")
con.sql("""select count(*) filter (is_ai) ai_rows, count(distinct canon) filter (is_ai) ai_canon, count(*) filter (is_ai and renamed) ai_renamed,
           count(*) filter (is_ai and not found) ai_not_found, count(*) filter (is_ai and by_name and not by_topic and not by_desc) name_only,
           count(*) filter (is_ai and not by_name and not by_topic and by_desc) desc_only from u""").show()
old = {r[0].lower() for r in con.execute(f"select repo from read_parquet('{D}/ai_repo_universe_low.parquet')").fetchall()}
low = {r[0].lower(): r for r in con.execute("select repo, is_ai, canon, renamed, stars_sample from u").fetchall()}
print(f"AI rows of this universe whose exact name is ALSO in the 2025-based universe: {sum(1 for k, v in low.items() if v[1] and k in old)} of {sum(v[1] for v in low.values())}")
for fname in ("ai_reference_repos.txt", "ai_reference_repos_2.txt", "ai_reference_repos_3.txt"):
    refs = [l.strip() for l in open(f"{ROOT}/scripts/{fname}", encoding="utf-8") if l.strip() and not l.startswith("#")]
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r) for r in refs)
    ins = [r for r in refs if r.lower() in low]
    ai = [r for r in ins if low[r.lower()][1]]
    in_old = [r for r in ins if r.lower() in old]
    print(f"\n== {fname}: {len(refs)} listed, {len(ins)} with >= 30 stars in the 2023-2024 sample")
    print(f"   recall, sample-based universe : {len(ai)}/{len(ins)} = {100 * len(ai) / max(1, len(ins)):.0f}%")
    print(f"   present in the 2025-based universe (exact name): {len(in_old)}/{len(ins)} = {100 * len(in_old) / max(1, len(ins)):.0f}%")
    print("   missed by sample-based rules:", [r for r in ins if not low[r.lower()][1]])
    print("   renamed (old name -> current):", [(r, low[r.lower()][2]) for r in ins if low[r.lower()][3]])
    print("   not in sample pool:", [r for r in refs if r.lower() not in low])
