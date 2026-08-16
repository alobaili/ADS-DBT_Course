{{ config(materialized='view') }}

-- Reference data arrives as a dbt seed: small, static, and version-controlled
-- alongside the models that use it.

select * from {{ ref('departments') }}
