{{ config(severity='warn') }}
-- Hours flagged low/high INSIDE the window we call trusted. Expected today (2 known rows): 2025-04-13 and 2025-05-08 01:00 UTC
-- (the latter downloaded `ok` but holds ~12% of normal events). Warn, not error: a few odd hours do not invalidate the window.
select hr, events, base_events, events_ratio, flag
from {{ ref('fct_hourly_quality') }}
where flag in ('low', 'high')
  and hr < '{{ var("window_end") }}'
