-- One row per (contributor, 7-day block): was the person active on an AI-candidate repo that block, and did they push/PR code?
-- Contributor = non-bot actor with a Push/PR/Issue/comment/review event (stars and forks are consumption, not contribution).
-- Blocks start at window_start; only full blocks are kept (retention_blocks of them).
select actor,
       ((ts::date - date '{{ var("window_start") }}') // 7)::int as blk,
       bool_or(type in ('PushEvent', 'PullRequestEvent')) as did_code
from {{ ref('stg_events') }}
where ts >= '{{ var("window_start") }}'
  and ts <  date '{{ var("window_start") }}' + {{ var('retention_blocks') * 7 }}
  and type in ('PushEvent', 'PullRequestEvent', 'IssuesEvent', 'IssueCommentEvent',
               'PullRequestReviewEvent', 'PullRequestReviewCommentEvent')
  and actor is not null
  and actor not ilike '%[bot]' and actor not ilike '%-bot'
  and repo in (select repo from {{ ref('int_ai_repo_candidates') }})
group by 1, 2
