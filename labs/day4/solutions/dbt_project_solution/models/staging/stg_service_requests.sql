{{ config(materialized='view') }}

/*
    Staging: type, clean and deduplicate the raw request feed.

    One row per request_id. This is the model that closes the duplicate question
    Day 1 left open: a full-row dedupe removes only 33 of the 60 duplicated
    requests, because 27 pairs were written by two systems using different date
    formats and are therefore not byte-identical. Deduplicating on the business
    key catches all 60.
*/

with source as (

    select * from {{ source('raw', 'service_requests') }}

),

typed as (

    select
        request_id::integer                                     as request_id,
        {{ parse_mixed_timestamp('submitted_at') }}             as submitted_at,
        to_timestamp(nullif(resolved_at, ''), 'YYYY-MM-DD HH24:MI:SS')::timestamp
                                                                as resolved_at,
        service_id::integer                                     as service_id,
        channel_id::integer                                     as channel_id,
        district_id::integer                                    as district_id,
        department_id::integer                                  as department_id,
        {{ clean_priority('priority') }}                        as priority,
        status                                                  as status,

        -- Impossible durations are nulled, not deleted. The request is real even
        -- when its recorded duration is not, and it still counts in volume.
        --
        -- The upper bound of 8760 hours (one year) is carried over unchanged from
        -- the Day 1 notebook. The change is at the lower bound: Day 1 used < 0 and
        -- deliberately kept zero as an open question about where to draw the line.
        -- This is that question answered. A request resolved in zero hours did not
        -- happen, and every one of those rows was scoring as an SLA success.
        case
            when resolution_hours::numeric <= 0    then null
            when resolution_hours::numeric > 8760  then null
            else resolution_hours::numeric
        end                                                     as resolution_hours,

        nullif(satisfaction_score, '')::numeric                 as satisfaction_score,

        -- Two spellings of "missing" are folded into one honest NULL.
        nullif(nullif(trim(citizen_age_band), ''), 'Unknown')   as citizen_age_band,

        -- Retained so the exact fault is auditable downstream rather than lost.
        (resolution_hours::numeric <= 0 or resolution_hours::numeric > 8760)
                                                                as has_invalid_duration

    from source

),

deduplicated as (

    select
        *,
        row_number() over (
            partition by request_id
            -- Prefer the ISO-formatted copy: it is the unambiguous representation,
            -- so the choice is defensible rather than arbitrary.
            order by case when submitted_at is not null then 0 else 1 end,
                     resolved_at nulls last
        ) as row_num
    from typed

)

select
    request_id,
    submitted_at,
    resolved_at,
    service_id,
    channel_id,
    district_id,
    department_id,
    priority,
    status,
    resolution_hours,
    satisfaction_score,
    citizen_age_band,
    has_invalid_duration,

    -- An impossible ordering: flagged, not silently corrected.
    (resolved_at is not null and resolved_at < submitted_at) as has_impossible_timestamps

from deduplicated
where row_num = 1
