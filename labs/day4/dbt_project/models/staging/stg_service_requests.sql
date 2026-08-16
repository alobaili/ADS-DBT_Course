{{ config(materialized='view') }}

/*
    LAB 1, STEP 3.  Staging: type, clean and deduplicate the raw request feed.

    Target: exactly 12,000 rows, one per request_id.

    The macros parse_mixed_timestamp() and clean_priority() are provided in
    macros/ . Call them rather than writing the regex yourself.
*/

with source as (

    select * from {{ source('raw', 'service_requests') }}

),

typed as (

    select
        request_id::integer as request_id

        -- TODO (a): parse submitted_at with the provided macro, and cast
        --           resolved_at (remember it is empty string, not null, when absent)

        -- TODO (b): cast service_id, channel_id, district_id, department_id to integer

        -- TODO (b): clean priority with the provided macro

        -- TODO (c): null resolution_hours where it is <= 0 or > 8760,
        --           and keep a has_invalid_duration flag so the fault stays auditable

        -- TODO: fold blank and 'Unknown' citizen_age_band into a single NULL

    from source

),

deduplicated as (

    -- TODO (d): rank rows within each request_id with row_number(), preferring the
    --           copy whose timestamp parsed cleanly, then keep only the first.
    select * from typed

)

select * from deduplicated
