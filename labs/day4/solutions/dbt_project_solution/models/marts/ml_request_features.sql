/*
    The Day 3 modelling table, rebuilt as a governed, tested model.

    Column-for-column identical to data/processed/service_requests_features.csv,
    with one deliberate difference: this model has 12,000 rows against the CSV's
    12,027, because the CSV was deduplicated on the full row and therefore still
    carries 27 requests twice. See the Day 4 companion guide.
*/

select
    sla_met,
    resolution_hours,
    submitted_hour,
    submitted_dow,
    submitted_month,
    is_weekend,
    is_digital::int as is_digital,
    population,
    priority_rank,
    target_resolution_hours,
    satisfaction_score
from {{ ref('int_requests_enriched') }}
