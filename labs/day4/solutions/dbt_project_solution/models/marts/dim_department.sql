select
    department_id,
    department_name
from {{ ref('stg_departments') }}
