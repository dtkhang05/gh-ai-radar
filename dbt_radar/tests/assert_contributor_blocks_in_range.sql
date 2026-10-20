-- Blocks must be 0 .. retention_blocks-1; anything else means the window arithmetic is wrong.
select actor, blk
from {{ ref('fct_contributor_week') }}
where blk < 0 or blk > {{ var('retention_blocks') - 1 }}
