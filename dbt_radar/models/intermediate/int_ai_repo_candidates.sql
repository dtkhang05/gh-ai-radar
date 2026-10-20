-- AI repo universe: repos that got >= min_stars stars inside the trusted window AND were classified as AI by at least one signal
-- (name keywords, GitHub topics, description) in scripts/ai_repos_classify.py. That script's output is a snapshot of GitHub metadata
-- fetched in 2026, so topics/descriptions describe the repo today, not in 03-05/2025; repos the API could not find
-- (renamed/deleted/private) can only match by name. Pool is limited to the 20,000 most-starred repos of the window (>= ~98 stars).
-- Measured recall on two hand-picked lists: 82% and 89% (name filter alone: 25% and 20%); see ../PLAN.md Phase 5.
-- The universe is joined BEFORE grouping so only ~4,000 repos are aggregated, not every repo in the window (that spilled past the temp cap).
with universe as (
    select repo, by_name, by_topic, by_desc from read_parquet('{{ var("ai_universe_parquet") }}')
)
select e.repo,
       count(*) as events,
       count(*) filter (where e.type = 'WatchEvent') as stars,
       any_value(u.by_name) as by_name, any_value(u.by_topic) as by_topic, any_value(u.by_desc) as by_desc
from {{ ref('stg_events') }} e
join universe u using (repo)
where e.ts >= '{{ var("window_start") }}' and e.ts < '{{ var("window_end") }}'
group by e.repo
having count(*) filter (where e.type = 'WatchEvent') >= {{ var('min_stars') }}
