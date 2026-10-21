{{ config(enabled=var('with_sample', false)) }}
-- The multi-year sample must have exactly sample_expected_days days with 24 hourly files each, and no hour with 0 events.
-- Returns one row per problem; the build fails if there is any.
select 'days' as problem, count(distinct d) as n from {{ ref('fct_hourly_quality_sample') }} having count(distinct d) <> {{ var('sample_expected_days') }}
union all
select 'hours_on_' || d::varchar, count(*) from {{ ref('fct_hourly_quality_sample') }} group by d having count(*) <> 24
union all
select 'missing_' || hr::varchar, events from {{ ref('fct_hourly_quality_sample') }} where flag = 'missing'
