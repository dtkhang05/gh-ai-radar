# Multi-year sample: download 3 full days per month (the 2nd, 3rd and 4th Wednesday) for 2023-01 .. 2024-12 into data/parquet_sample/,
# using the same per-hour logic as ingest.py (download -> 5 columns -> Parquet -> delete raw). Resumable: finished hours are skipped.
# Why Wednesdays: the weekday is held fixed so a month-to-month change is not a weekday effect (weekends have ~20% fewer events).
# Usage: python -I -X utf8 scripts/ingest_sample.py [workers] [first_month YYYY-MM] [last_month YYYY-MM]
import importlib.util, os, sys, time, json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["RADAR_PQ_DIR"] = os.path.join(ROOT, "data", "parquet_sample")
os.environ["RADAR_MANIFEST"] = os.path.join(ROOT, "data", "manifest_sample.jsonl")
spec = importlib.util.spec_from_file_location("ingest", os.path.join(ROOT, "scripts", "ingest.py"))   # -I drops the script dir from sys.path
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def sample_days(first, last):
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    while (y, m) <= (ly, lm):
        wednesdays = [d for d in (date(y, m, i) for i in range(1, 29)) if d.weekday() == 2]   # 4 of them in every month
        yield from wednesdays[1:4]
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    first = sys.argv[2] if len(sys.argv) > 2 else "2023-01"
    last = sys.argv[3] if len(sys.argv) > 3 else "2024-12"
    todo = [datetime(d.year, d.month, d.day) + timedelta(hours=h) for d in sample_days(first, last) for h in range(24)]
    print(f"{len(todo)} hours on {len(todo) // 24} days, {first} .. {last}", flush=True)
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
