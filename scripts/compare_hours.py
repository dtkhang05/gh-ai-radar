# Count events per type in hourly GH Archive files, to spot data loss across months.
# Usage: python -I -X utf8 scripts/compare_hours.py data/2024-10-19-12.json.gz data/2026-10-19-12.json.gz ...
import duckdb, os, sys
con = duckdb.connect()
for f in sys.argv[1:]:
    r = con.sql(f"""select count(*), count(*) filter (type='WatchEvent'), count(*) filter (type='ForkEvent'),
      count(*) filter (type='PushEvent')
      from read_json('{f}', format='newline_delimited', ignore_errors=true, columns={{type:'VARCHAR'}})""").fetchone()
    print(os.path.basename(f), "total/watch/fork/push:", r)
