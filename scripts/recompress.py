# One-off: rewrite hourly Parquet files written by the first ingest.py (VARCHAR id, default zstd, unsorted)
# into the current layout (BIGINT id, sorted by repo, zstd 9). Skips files that already have a BIGINT id.
# Usage: python -I -X utf8 scripts/recompress.py
import duckdb, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
before = after = n = 0
for f in sorted(glob.glob(os.path.join(ROOT, "data", "parquet", "*.parquet"))):
    p = f.replace("\\", "/")
    if duckdb.sql(f"select typeof(id) from read_parquet('{p}') limit 1").fetchone()[0] == "BIGINT":
        continue
    tmp = p + ".tmp"
    duckdb.execute(f"""copy (select try_cast(id as bigint) id, type, ts, actor, repo from read_parquet('{p}') order by repo, ts)
                       to '{tmp}' (format parquet, compression zstd, compression_level 9)""")
    # same row count or abort: never replace a file with a different one
    assert duckdb.sql(f"select count(*) from read_parquet('{tmp}')").fetchone() == duckdb.sql(f"select count(*) from read_parquet('{p}')").fetchone(), f
    before += os.path.getsize(f); after += os.path.getsize(tmp)
    os.replace(tmp, f)
    n += 1
    if n % 100 == 0:
        print(n, f"{before/1e9:.2f} GB -> {after/1e9:.2f} GB", flush=True)
print("rewritten", n, f"{before/1e9:.2f} GB -> {after/1e9:.2f} GB")
