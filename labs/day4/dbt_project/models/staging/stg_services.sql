{{ config(materialized='view') }}

-- LAB 1, STEP 4.  Reference data arrives as a dbt seed.
-- TODO: select from the services seed using ref().

select 1 as todo
