select
    district_id,
    district_name,
    region,
    population
from {{ ref('stg_districts') }}
