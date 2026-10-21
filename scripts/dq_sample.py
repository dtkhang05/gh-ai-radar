# Data-quality check for the multi-year sample (data/parquet_sample, 72 Wednesdays 2023-01 .. 2024-12).
# Each hour is compared with the median of the SAME hour on the 6 nearest other sample days (3 before, 3 after, so about +-1.5 months):
# a centered baseline, because with only 3 days a month a trailing 4-week baseline would not exist. Same thresholds as the 2025 layer:
# low < 0.70, high > 1.50, missing = 0 events. Event counts come from the ingest manifest (written when each hour was processed).
# Usage: python -I -X utf8 scripts/dq_sample.py
import json, os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "manifest_sample.jsonl")
OUT = os.path.join(ROOT, "data", "derived", "dq_sample_hours.parquet")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

rows = [json.loads(l) for l in open(MANIFEST, encoding="utf-8")]
con = duckdb.connect()
con.execute("set memory_limit='2GB'; set threads=2")
con.execute("create table m(file varchar, hour varchar, status varchar, events bigint, bytes_gz bigint)")
con.executemany("insert into m values (?,?,?,?,?)", [(r["file"], r["hour"], r["status"], r.get("events"), r.get("bytes_gz")) for r in rows])
print("manifest rows", con.sql("select count(*) from m").fetchone()[0], "distinct hours", con.sql("select count(distinct file) from m").fetchone()[0],
      "not ok", con.sql("select count(*) from m where status <> 'ok'").fetchone()[0])

con.execute("""create table h as
  select hour::timestamp hr, hour::timestamp::date d, hour(hour::timestamp) hod, events, bytes_gz from m where status = 'ok'""")
con.execute("""create table days as select d, row_number() over (order by d) n from (select distinct d from h)""")
con.execute("""create table q as
  select a.hr, a.d, a.hod, a.events, a.bytes_gz,
         (select median(b.events) from h b join days db using (d) where b.hod = a.hod and db.n between da.n - 3 and da.n + 3 and db.n <> da.n) base,
         (select median(b.bytes_gz) from h b join days db using (d) where b.hod = a.hod and db.n between da.n - 3 and da.n + 3 and db.n <> da.n) base_bytes
  from h a join days da using (d)""")
con.execute("""create table r as select *, round(events / base, 3) ratio, round(bytes_gz / base_bytes, 3) bytes_ratio,
                 case when events = 0 then 'missing' when events / base < 0.70 then 'low' when events / base > 1.50 then 'high' else 'ok' end flag from q""")
con.execute(f"copy r to '{OUT.replace(os.sep, '/')}' (format parquet)")

print("\nhours per flag:", con.sql("select flag, count(*) from r group by 1 order by 1").fetchall())
print("\nflagged hours (hr, events, base, ratio, bytes_ratio):")
for row in con.sql("select hr::varchar, events, round(base), ratio, bytes_ratio, flag from r where flag <> 'ok' order by hr").fetchall():
    print("  ", row)
print("\nhours with fewer than 24 files per day:", con.sql("select d::varchar, count(*) from h group by 1 having count(*) <> 24").fetchall())
print("\nper-day total events (millions) by quarter: min / median / max, days")
for row in con.sql("""select year(d) || '-Q' || quarter(d) q, round(min(t) / 1e6, 2), round(median(t) / 1e6, 2), round(max(t) / 1e6, 2), count(*)
                       from (select d, sum(events) t from h group by 1) group by 1 order by 1""").fetchall():
    print("  ", row)
print("\nlowest 5 days vs the median of the other days in the same quarter:")
for row in con.sql("""select d::varchar, round(t / 1e6, 2), round(t / median(t) over (partition by year(d), quarter(d)), 3) rel
                       from (select d, sum(events) t from h group by 1) order by rel limit 5""").fetchall():
    print("  ", row)
