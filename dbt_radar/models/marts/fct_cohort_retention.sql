-- Weekly cohort retention. Cohort c = contributors whose FIRST active block is c (c >= burn_in_blocks, so people active
-- before the burn-in ended are treated as existing, not new). kept = still active k blocks later anywhere in the AI repo set.
-- LEFT-CENSORING: no data before window_start, so early cohorts are inflated by dormant existing contributors; a falling
-- trend across cohorts is NOT evidence that the ecosystem is weakening.
with first_seen as (
    select actor, min(blk) as cohort_blk from {{ ref('fct_contributor_week') }} group by 1
),
cohort as (
    select f.actor, f.cohort_blk, w.did_code as first_is_code
    from first_seen f
    join {{ ref('fct_contributor_week') }} w on w.actor = f.actor and w.blk = f.cohort_blk
    where f.cohort_blk >= {{ var('burn_in_blocks') }}
      and f.cohort_blk <= {{ var('retention_blocks') - 2 }}
)
select c.cohort_blk, k.weeks_later, c.first_is_code,
       count(*) as cohort_size,
       count(*) filter (where exists (
           select 1 from {{ ref('fct_contributor_week') }} x
           where x.actor = c.actor and x.blk = c.cohort_blk + k.weeks_later)) as still_active
from cohort c
cross join (select unnest(range(1, 9)) as weeks_later) k
where c.cohort_blk + k.weeks_later <= {{ var('retention_blocks') - 1 }}
group by all
