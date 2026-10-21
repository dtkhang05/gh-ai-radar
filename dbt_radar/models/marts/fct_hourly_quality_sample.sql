{{ config(enabled=var('with_sample', false)) }}
-- Data-quality layer for the multi-year sample (data/parquet_sample: 3 Wednesdays a month, 2023-01 .. 2024-12; scripts/ingest_sample.py).
-- Same thresholds as fct_hourly_quality (low < 0.70, high > 1.50, missing = 0 events), but the baseline is CENTERED: with only 3 days a month
-- a trailing 4-week window does not exist, so each hour is compared with the median of the SAME hour on the 6 nearest other sample days
-- (3 before, 3 after, about +-1.5 months). Weakness: a sustained drop longer than ~3 months would also lower its own baseline and go unseen.
-- The hour comes from the file name (YYYY-MM-DD-H.parquet), the same definition as the ingest manifest, so rows are per downloaded file.
-- Enabled only when with_sample is true (run_pipeline.py sets it when data/parquet_sample exists), so CI without the sample still builds.
with files as (
    select regexp_extract(filename, '(\d{4}-\d{2}-\d{2})-(\d{1,2})\.parquet$', 1) as d_txt,
           regexp_extract(filename, '(\d{4}-\d{2}-\d{2})-(\d{1,2})\.parquet$', 2)::int as hod,
           count(*) as events
    from read_parquet('{{ var("sample_parquet_glob") }}', filename = true)
    group by 1, 2
),
j as (
    select d_txt::date as d, hod, d_txt::date::timestamp + to_hours(hod) as hr, events from files
),
days as (
    select d, row_number() over (order by d) as n from (select distinct d from j)
),
b as (
    select a.hr, a.d, a.hod, a.events, median(o.events) as base_events, count(*) as n_base
    from j a
    join days da on da.d = a.d
    join days db on db.n between da.n - 3 and da.n + 3 and db.n <> da.n
    join j o on o.d = db.d and o.hod = a.hod
    group by a.hr, a.d, a.hod, a.events
)
select hr, d, hod, events, base_events,
       round(events / base_events, 3) as events_ratio,
       case when events = 0 then 'missing'
            when events / base_events < 0.70 then 'low'
            when events / base_events > 1.50 then 'high'
            else 'ok' end as flag
from b
