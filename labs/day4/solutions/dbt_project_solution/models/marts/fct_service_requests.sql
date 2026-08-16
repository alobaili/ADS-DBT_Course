/*
    The grain statement for this model is one row per service request.
    Foreign keys point at the dimensions; measures and the SLA outcome live here.
*/

select
    request_id,
    service_id,
    channel_id,
    district_id,
    department_id,
    submitted_at,
    resolved_at,
    submitted_month_start,
    status,
    priority,
    priority_rank,
    resolution_hours,
    target_resolution_hours,
    sla_met,
    resolution_band,
    satisfaction_score,
    is_open,
    has_invalid_duration,
    has_impossible_timestamps
from {{ ref('int_requests_enriched') }}
