{{ config(materialized='view') }}

/*
    A complete month spine covering the data window.

    Why a spine at all: a month in which a department opened no requests would
    simply be missing from a GROUP BY, and a missing month reads as a gap in the
    chart rather than a zero. Reporting grains must be dense, not sparse.

    Written in plain SQL rather than dbt_utils.date_spine so the mechanics stay
    visible, and so the model builds with no packages installed.
*/

with bounds as (
    select
        date_trunc('month', min(submitted_at))::date as first_month,
        date_trunc('month', max(submitted_at))::date as last_month
    from {{ ref('int_requests_enriched') }}
)

select
    generate_series(first_month, last_month, interval '1 month')::date as month_start
from bounds
