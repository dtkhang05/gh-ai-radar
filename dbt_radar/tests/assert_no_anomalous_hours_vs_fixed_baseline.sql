{{ config(severity='warn') }}
-- Same idea as assert_no_anomalous_hours_in_trusted_window but against the frozen baseline (fixed_flag), which still sees a
-- sustained drop after the rolling baseline has adapted to it. Expected today (2 known rows): 2025-04-13 and 2025-05-08 01:00 UTC.
select hr, events, fixed_base_events, fixed_ratio, fixed_flag
from {{ ref('fct_hourly_quality') }}
where fixed_flag in ('low', 'high')
  and hr < '{{ var("window_end") }}'
