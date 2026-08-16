{{ config(materialized='view') }}

/*
    LAB 2, STEP 1.  One row per request, with every dimension attached and every
    derived attribute computed once. Marts read from here.

    Target: 12,000 rows, 10,437 with a non-null sla_met, 1,524 still open.
*/

with requests as (
    select * from {{ ref('stg_service_requests') }}
)

-- TODO: left join stg_services, stg_channels, stg_districts and stg_departments.
--       Use LEFT joins: an inner join would silently drop rows.

-- TODO: derive submitted_hour, submitted_dow, submitted_month, is_weekend.
--       Day of week must follow the Python convention used on Days 1 to 3,
--       which is extract(isodow) - 1, NOT extract(dow).

-- TODO: derive priority_rank (Low 0, Medium 1, High 2).

-- TODO: define sla_met ONCE, here. NULL when the request is open, and NULL
--       when resolution_hours is null. Otherwise 1 if within target, else 0.

-- TODO: derive resolution_band with the provided macro, and is_open.

select * from requests
