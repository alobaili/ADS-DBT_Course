-- The SLA flag must always be reproducible from the duration and the target.
-- Guards against the definition drifting away from its own inputs.
select request_id, resolution_hours, target_resolution_hours, sla_met
from {{ ref('fct_service_requests') }}
where sla_met is not null
  and sla_met <> case when resolution_hours <= target_resolution_hours then 1 else 0 end
