-- Cleaning only: drop rows that cannot be placed in time or identified (1 all-NULL row seen in 150M rows).
-- Duplicate ids (55 in 150M rows) are NOT removed here: deduplicating 300M+ rows needs a global hash; the star fact counts distinct ids instead.
select id, type, ts, actor, repo
from {{ source('gharchive', 'events') }}
where id is not null and ts is not null
