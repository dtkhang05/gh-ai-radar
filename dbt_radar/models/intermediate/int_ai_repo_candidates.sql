-- AI repo candidates: repo name matches the AI pattern AND the repo got >= min_stars stars inside the trusted window.
-- Note the selection bias: popular-in-this-window repos only; AI repos with plain names are missed (recall unmeasured).
select repo,
       count(*) as events,
       count(*) filter (where type = 'WatchEvent') as stars
from {{ ref('stg_events') }}
where ts >= '{{ var("window_start") }}' and ts < '{{ var("window_end") }}'
  and repo is not null
  and regexp_matches(split_part(lower(repo), '/', 2), '{{ ai_name_pattern() }}')
group by repo
having count(*) filter (where type = 'WatchEvent') >= {{ var('min_stars') }}
