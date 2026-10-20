-- Days a repo got abnormally many stars. A SUSPICION signal only: a viral post or a launch also causes a spike.
-- Definition (thresholds are vars): stars >= spike_min_stars AND >= spike_multiple x median of the prior 14 days,
-- and the repo had stars on >= min_hist_days of those 14 days (otherwise the launch day of a new repo counts as a spike).
with w as (
    select repo, d, stars,
           median(stars) over prior as baseline,
           count(*) over prior as prior_days,
           sum((stars > 0)::int) over prior as prior_days_with_stars
    from {{ ref('fct_star_daily') }}
    window prior as (partition by repo order by d rows between 14 preceding and 1 preceding)
)
select repo, d, stars, round(baseline, 1) as baseline,
       round(stars / greatest(baseline, 1), 1) as x_baseline
from w
where prior_days >= 7
  and prior_days_with_stars >= {{ var('min_hist_days') }}
  and stars >= {{ var('spike_min_stars') }}
  and stars >= {{ var('spike_multiple') }} * greatest(baseline, 1)
