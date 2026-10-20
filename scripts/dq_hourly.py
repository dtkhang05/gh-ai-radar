# Phase 3: data-quality check. For every hour, compare event counts to the median of the same
# weekday+hour in the previous 4 weeks, and flag hours that are missing, too low or too high.
# Needs data/radar.duckdb (run build_db.py first).
# Usage: python -I -X utf8 scripts/dq_hourly.py
import duckdb, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOW, HIGH = 0.70, 1.50  # ratio thresholds vs baseline; the May-2025 drop was ~0.6
con = duckdb.connect(os.path.join(ROOT, "data", "radar.duckdb"))
# shared machine (other project runs Docker): cap resources so one query cannot exhaust RAM or disk
con.execute("set memory_limit='3GB'; set threads=4; set max_temp_directory_size='5GB'")
con.execute(f"""
create or replace table dq_hourly as
with counts as (
  select date_trunc('hour', ts) hr, count(*) events,
         count(*) filter (type = 'WatchEvent') stars,
         count(*) filter (type = 'PushEvent') pushes
  from raw_events where ts is not null group by 1
), calendar as (  -- every hour expected between first and last data, so a missing file shows up as a row
  select unnest(generate_series((select min(hr) from counts), (select max(hr) from counts), interval 1 hour)) hr
), j as (
  select c.hr, coalesce(n.events, 0) events, coalesce(n.stars, 0) stars, coalesce(n.pushes, 0) pushes,
         dayofweek(c.hr) dow, extract(hour from c.hr) hod
  from calendar c left join counts n using (hr)
), b as (
  select *,
    -- 4 prior same weekday+hour values; median is robust to one odd week
    median(events) over w base_events, median(stars) over w base_stars, count(*) over w n_base
  from j window w as (partition by dow, hod order by hr rows between 4 preceding and 1 preceding)
)
select hr, events, stars, pushes, base_events, base_stars,
  round(events / base_events, 3) events_ratio, round(stars / nullif(base_stars, 0), 3) stars_ratio,
  case when n_base < 3 then 'no_baseline'
       when events = 0 then 'missing'
       when events / base_events < {LOW} then 'low'
       when events / base_events > {HIGH} then 'high'
       else 'ok' end flag
from b order by hr
""")
print("flag counts:")
con.sql("select flag, count(*) hrs from dq_hourly group by 1 order by 2 desc").show()
print("flagged hours per day:")
con.sql("""select hr::date d, flag, count(*) hrs, round(min(events_ratio), 2) min_ratio
           from dq_hourly where flag in ('missing', 'low', 'high') group by 1, 2 order by 1""").show(max_rows=60)
