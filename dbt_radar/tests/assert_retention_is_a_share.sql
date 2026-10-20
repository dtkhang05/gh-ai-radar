-- Retained people can never outnumber the cohort they come from.
select cohort_blk, weeks_later, first_is_code, cohort_size, still_active
from {{ ref('fct_cohort_retention') }}
where still_active > cohort_size or still_active < 0 or cohort_size <= 0
