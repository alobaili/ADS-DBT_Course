{{ config(materialized='view') }}

-- LAB 2, STEP 4a.  A complete month spine covering the data window.
-- A month with no activity must still appear, or the backlog trend has holes.
-- TODO: use generate_series over the min and max submitted_at, truncated to month.

select null::date as month_start
