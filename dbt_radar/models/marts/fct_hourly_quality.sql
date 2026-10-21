-- Data-quality layer: every expected hour in [dq_start, dq_end) compared with the median of the same weekday+hour
-- in the previous 4 weeks. A missing file shows up as a row with 0 events (the calendar is built, not read from data).
-- Known weakness: the rolling baseline adapts to a sustained drop, so a long outage is flagged for ~2-3 weeks only.
-- Second check, fixed_*: the same ratio against a baseline frozen from the first dq_fixed_weeks weeks (median per weekday+hour),
-- which does not adapt. Hours inside that reference window get 'reference' (they would be compared with themselves).
-- Weakness of the fixed one: it cannot tell a real fault from a genuine long-term level change (growth, seasonality).
with counts as (
    select date_trunc('hour', ts) as hr,
           count(*) as events,
           count(*) filter (where type = 'WatchEvent') as stars,
           count(*) filter (where type = 'PushEvent') as pushes
    from {{ ref('stg_events') }}
    where ts >= '{{ var("dq_start") }}' and ts < '{{ var("dq_end") }}'
    group by 1
),
calendar as (
    select unnest(generate_series(timestamp '{{ var("dq_start") }}', timestamp '{{ var("dq_end") }}' - interval 1 hour, interval 1 hour)) as hr
),
j as (
    select c.hr, coalesce(n.events, 0) as events, coalesce(n.stars, 0) as stars, coalesce(n.pushes, 0) as pushes,
           dayofweek(c.hr) as dow, extract(hour from c.hr) as hod
    from calendar c left join counts n using (hr)
),
b as (
    select *, median(events) over w as base_events, median(stars) over w as base_stars, count(*) over w as n_base
    from j
    window w as (partition by dow, hod order by hr rows between 4 preceding and 1 preceding)
),
fixed as (
    select dow, hod, median(events) as fixed_base_events
    from j
    where hr < timestamp '{{ var("dq_start") }}' + to_weeks({{ var("dq_fixed_weeks") }})
    group by 1, 2
)
select b.hr, b.events, b.stars, b.pushes, b.base_events, b.base_stars,
       round(b.events / b.base_events, 3) as events_ratio,
       round(b.stars / nullif(b.base_stars, 0), 3) as stars_ratio,
       case when b.n_base < 3 then 'no_baseline'
            when b.events = 0 then 'missing'
            when b.events / b.base_events < 0.70 then 'low'
            when b.events / b.base_events > 1.50 then 'high'
            else 'ok' end as flag,
       f.fixed_base_events,
       round(b.events / f.fixed_base_events, 3) as fixed_ratio,
       case when b.hr < timestamp '{{ var("dq_start") }}' + to_weeks({{ var("dq_fixed_weeks") }}) then 'reference'
            when b.events = 0 then 'missing'
            when b.events / f.fixed_base_events < 0.70 then 'low'
            when b.events / f.fixed_base_events > 1.50 then 'high'
            else 'ok' end as fixed_flag
from b join fixed f using (dow, hod)
