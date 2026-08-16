select
    service_id,
    service_name,
    category as service_category,
    target_resolution_hours
from {{ ref('stg_services') }}
