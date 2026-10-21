# Ingest GH Archive hours: download -> slim to Parquet -> delete raw file -> log stats to manifest.
# Usage: python -I -X utf8 scripts/ingest.py <start YYYY-MM-DD> <end YYYY-MM-DD inclusive> [workers] [max_hours]
import duckdb, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
# The multi-year sample (scripts/ingest_sample.py) writes to its own folder so the 2025 pipeline glob never sees it.
PQ = os.environ.get("RADAR_PQ_DIR", os.path.join(ROOT, "data", "parquet"))
MANIFEST = os.environ.get("RADAR_MANIFEST", os.path.join(ROOT, "data", "manifest.jsonl"))
os.makedirs(RAW, exist_ok=True)
os.makedirs(PQ, exist_ok=True)


def hours(start, end):
    t = datetime.strptime(start, "%Y-%m-%d")
    stop = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
    while t < stop:
        yield t
        t += timedelta(hours=1)


def download(url, dest, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gh-ai-radar/0.1 (personal learning project)"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404"
            err = f"http {e.code}"
        except Exception as e:
            err = type(e).__name__
        time.sleep(2 ** i)
    return err


def process(t):
    name = f"{t:%Y-%m-%d}-{t.hour}"
    out = os.path.join(PQ, name + ".parquet")
    if os.path.exists(out):
        return None  # already done
    raw = os.path.join(RAW, name + ".json.gz")
    t0 = time.time()
    rec = {"hour": f"{t:%Y-%m-%d %H}:00", "file": name}
    err = download(f"https://data.gharchive.org/{name}.json.gz", raw)
    if err:
        rec.update(status="missing" if err == "404" else "error", detail=err)
    else:
        try:
            rec["bytes_gz"] = os.path.getsize(raw)
            con = duckdb.connect()
            # shared machine (other project runs Docker): cap each worker's connection
            con.execute("set memory_limit='1GB'; set threads=2; set max_temp_directory_size='2GB'")
            con.execute(f"""
              create table ev as
              select id, type, created_at::timestamp as ts, actor.login as actor, repo.name as repo
              from read_json('{raw}', format='newline_delimited', ignore_errors=true,
                columns={{id:'VARCHAR', type:'VARCHAR', created_at:'VARCHAR',
                         actor:'STRUCT(login VARCHAR)', repo:'STRUCT(name VARCHAR)'}})""")
            rec["events"] = con.sql("select count(*) from ev").fetchone()[0]
            rec["by_type"] = dict(con.sql("select type, count(*) from ev group by 1").fetchall())
            tmp = out + ".tmp"
            # id as BIGINT + sort by repo + zstd level 9: ~29% smaller than defaults (measured on 24 hours of 2025-04-15)
            con.execute(f"""copy (select try_cast(id as bigint) id, type, ts, actor, repo from ev order by repo, ts)
                            to '{tmp}' (format parquet, compression zstd, compression_level 9)""")
            os.replace(tmp, out)
            rec["bytes_pq"] = os.path.getsize(out)
            rec["status"] = "ok"
            con.close()
        except Exception as e:
            rec.update(status="error", detail=f"{type(e).__name__}: {e}"[:200])
    if os.path.exists(raw):
        os.remove(raw)
    rec["secs"] = round(time.time() - t0, 1)
    return rec


if __name__ == "__main__":
    start, end = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
    todo = list(hours(start, end))[:limit]
    t0, done = time.time(), 0
    with ThreadPoolExecutor(workers) as ex, open(MANIFEST, "a", encoding="utf-8") as mf:
        for rec in ex.map(process, todo):
            done += 1
            if rec:
                mf.write(json.dumps(rec) + "\n")
                mf.flush()
            if done % 24 == 0 or done == len(todo):
                print(f"{done}/{len(todo)} hours, {time.time()-t0:.0f}s", flush=True)
    print("finished", round(time.time() - t0), "s")
