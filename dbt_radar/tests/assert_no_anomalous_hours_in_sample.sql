{{ config(enabled=var('with_sample', false), severity='warn') }}
-- Hours of the sample that are far from the same hour on neighbouring sample days. Expected today (11 rows, see PLAN.md section 4):
-- 14/08/2024 23:00 UTC (source fault, 489 events), 12/04/2023 02-04h (dependabot burst), and a few hours with no explanation yet.
select hr, events, base_events, events_ratio, flag
from {{ ref('fct_hourly_quality_sample') }}
where flag in ('low', 'high')
