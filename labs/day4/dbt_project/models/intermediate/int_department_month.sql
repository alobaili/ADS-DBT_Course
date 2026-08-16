{{ config(materialized='view') }}

-- LAB 2, STEP 4a.  The dense department-by-month grid.
-- TODO: cross join stg_departments to int_date_spine. Expect 5 x 14 = 70 rows.

select null::int as department_id
