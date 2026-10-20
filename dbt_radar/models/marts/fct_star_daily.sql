-- Stars per AI-candidate repo per day, dense (zero days included so rolling baselines are not biased upward).
with stars as (
    select repo, ts::date as d, count(distinct id) as stars
    from {{ ref('stg_events') }}
    where type = 'WatchEvent' and actor is not null
      and ts >= '{{ var("window_start") }}' and ts < '{{ var("window_end") }}'
      and repo in (select repo from {{ ref('int_ai_repo_candidates') }})
    group by 1, 2
),
calendar as (
    select repo,
           unnest(generate_series(date '{{ var("window_start") }}', date '{{ var("window_end") }}' - 1, interval 1 day))::date as d
    from {{ ref('int_ai_repo_candidates') }}
)
select c.repo, c.d, coalesce(s.stars, 0) as stars
from calendar c
left join stars s using (repo, d)
