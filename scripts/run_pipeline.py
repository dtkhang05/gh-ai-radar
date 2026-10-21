# One command for the whole chain: preflight -> (optional) ingest -> dbt build (models + tests) -> summary.
# Fail-fast: a failing step stops the run and the exit code is non-zero. dbt test WARNINGS do not fail the run but are listed.
# Everything is logged with timestamps to logs/pipeline.log.
# Usage: python -X utf8 scripts/run_pipeline.py                                  (dbt only, on the Parquet already on disk)
#        python -X utf8 scripts/run_pipeline.py --ingest 2025-03-01 2025-03-31   (download missing hours first; skips finished ones)
import argparse, json, os, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = ROOT / "dbt_radar"
DATA = ROOT / "data"
LOG = ROOT / "logs" / "pipeline.log"
MIN_FREE_GB = 20  # refuse to start with less free disk than this (raw downloads + DuckDB temp files need headroom)

LOG.parent.mkdir(exist_ok=True)

def log(msg, echo=True):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if echo:
        print(line, flush=True)

def run(name, cmd, cwd, env=None):
    """Run a step, stream its output into the log, return its exit code."""
    t = time.time()
    log(f"START {name}: {' '.join(str(c) for c in cmd)}")
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace")
    tail = []
    for line in p.stdout:
        line = line.rstrip()
        log(f"  | {line}", echo=False)  # full output goes to the log file only
        tail.append(line)
        tail = tail[-6:]
    rc = p.wait()
    log(f"{'OK  ' if rc == 0 else 'FAIL'} {name} in {time.time() - t:.0f}s (exit {rc})")
    if rc != 0:
        for line in tail:
            print("     " + line)
    return rc

def manifest_lines():
    f = DATA / "manifest.jsonl"
    return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingest", nargs=2, metavar=("START", "END"), help="download hours for this inclusive date range first (YYYY-MM-DD)")
    ap.add_argument("--workers", type=int, default=2, help="download threads (default 2: the machine is shared)")
    args = ap.parse_args()
    t0 = time.time()
    log(f"=== pipeline start (log: {LOG}) ===")

    # 1) preflight: refuse to run blind
    free = shutil.disk_usage(ROOT).free / 1e9
    n_pq = len(list((DATA / "parquet").glob("*.parquet")))
    log(f"preflight: {n_pq} hourly Parquet files, {free:.1f} GB free disk")
    if n_pq == 0 and not args.ingest:
        log("FAIL preflight: no Parquet files and --ingest not given"); return 1
    if free < MIN_FREE_GB:
        log(f"FAIL preflight: only {free:.1f} GB free (< {MIN_FREE_GB} GB)"); return 1
    universe = DATA / "derived" / "ai_repo_universe.parquet"
    if not universe.exists():
        log("FAIL preflight: data/derived/ai_repo_universe.parquet missing; run top_repos_by_stars.py, "
            "fetch_repo_metadata.py and ai_repos_classify.py first (README, step 3)"); return 1

    # 2) ingest (optional). ingest.py exits 0 even when single hours fail, so also check the manifest for new bad rows.
    if args.ingest:
        before = len(manifest_lines())
        rc = run("ingest", [sys.executable, "-I", "-X", "utf8", str(ROOT / "scripts" / "ingest.py"), *args.ingest, str(args.workers)], ROOT)
        if rc != 0:
            return rc
        bad = [json.loads(l) for l in manifest_lines()[before:]]
        bad = [r for r in bad if r.get("status") != "ok"]
        if bad:
            log(f"FAIL ingest: {len(bad)} hours not ok, e.g. {[ (r['file'], r['status'], r.get('detail')) for r in bad[:3] ]}")
            return 1

    # 3) dbt build = run models + run tests in dependency order (a failing test blocks the models that depend on it)
    env = {**os.environ, "DBT_SEND_ANONYMOUS_USAGE_STATS": "False"}
    dbt = Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
    cmd = [str(dbt), "build", "--profiles-dir", ".", "--no-version-check"]
    if any((DATA / "parquet_sample").glob("*.parquet")):   # the 2023-2024 sample model and tests only exist when that data is on disk
        cmd += ["--vars", "{with_sample: true}"]
        log("multi-year sample found: building fct_hourly_quality_sample and its tests too")
    rc = run("dbt build", cmd, DBT_DIR, env)

    # 4) summary straight from dbt's own result file (not from parsing console text)
    rr = DBT_DIR / "target" / "run_results.json"
    status_counts, warns, errs = {}, [], []
    if rr.exists():
        for r in json.loads(rr.read_text(encoding="utf-8"))["results"]:
            status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
            if r["status"] == "warn":
                warns.append((r["unique_id"].split(".")[2], r.get("failures")))  # test.<project>.<name>[.<hash>]
            if r["status"] in ("error", "fail"):
                errs.append((r["unique_id"], r.get("message")))
    log(f"dbt results: {status_counts}")
    for name, n in warns:
        log(f"  WARN {name}: {n} rows")
    for name, msg in errs:
        log(f"  ERROR {name}: {msg}")
    log(f"=== pipeline {'FAILED' if rc != 0 or errs else 'finished OK'} in {time.time() - t0:.0f}s ===")
    return 1 if rc != 0 or errs else 0

if __name__ == "__main__":
    sys.exit(main())
