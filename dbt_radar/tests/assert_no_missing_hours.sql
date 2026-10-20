-- Every hour in the data-quality range must have a file with events. Fails the build if a whole hour is absent.
select hr, events, flag
from {{ ref('fct_hourly_quality') }}
where flag = 'missing'
