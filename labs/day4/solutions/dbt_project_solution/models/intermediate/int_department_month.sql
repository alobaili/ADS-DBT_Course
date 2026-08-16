{{ config(materialized='view') }}

/*
    The dense department-by-month grid the backlog mart aggregates onto.
    Every department appears in every month, whether or not it had activity.
*/

select
    d.department_id,
    d.department_name,
    s.month_start
from {{ ref('stg_departments') }} d
cross join {{ ref('int_date_spine') }} s
