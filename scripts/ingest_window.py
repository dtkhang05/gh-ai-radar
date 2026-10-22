# Continuous window of full days (not the Wednesday sample): download every hour of the days first..last into data/parquet_window/ with the same
# per-hour logic as ingest.py (download -> 5 columns -> Parquet -> delete raw). Used to find the day a signal seen in the sample begins.
# Kept apart from data/parquet_sample/ so the sample's "72 Wednesdays" structure (dbt tests, daily baselines) is not disturbed. Resumable.
# Usage: python -I -X utf8 scripts/ingest_window.py YYYY-MM-DD YYYY-MM-DD [workers]
import importlib.util, os, sys, time, json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["RADAR_PQ_DIR"] = os.path.join(ROOT, "data", "parquet_window")
os.environ["RADAR_MANIFEST"] = os.path.join(ROOT, "data", "manifest_window.jsonl")
spec = importlib.util.spec_from_file_location("ingest", os.path.join(ROOT, "scripts", "ingest.py"))   # -I drops the script dir from sys.path
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)

if __name__ == "__main__":
    first = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    last = datetime.strptime(sys.argv[2], "%Y-%m-%d")
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    todo = [first + timedelta(hours=h) for h in range(int((last - first).days + 1) * 24)]
    print(f"{len(todo)} hours on {len(todo) // 24} days, {sys.argv[1]} .. {sys.argv[2]}", flush=True)
    t0, done, bad = time.time(), 0, 0
    with ThreadPoolExecutor(workers) as ex, open(ingest.MANIFEST, "a", encoding="utf-8") as mf:
        for rec in ex.map(ingest.process, todo):
            done += 1
            if rec:
                mf.write(json.dumps(rec) + "\n")
                mf.flush()
                bad += rec["status"] != "ok"
            if done % 24 == 0 or done == len(todo):
                print(f"{done}/{len(todo)} hours, {time.time() - t0:.0f}s, not ok so far: {bad}", flush=True)
    print("finished", round(time.time() - t0), "s; not ok:", bad)
