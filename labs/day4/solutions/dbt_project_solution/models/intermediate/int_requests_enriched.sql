{{ config(materialized='view') }}

/*
    Intermediate: one row per request, with every dimension attached and every
    derived attribute computed once. Marts read from here, so a definition such
    as "SLA met" exists in exactly one place in the project.
*/

with requests as (
    select * from {{ ref('stg_service_requests') }}
),
services as (
    select * from {{ ref('stg_services') }}
),
channels as (
    select * from {{ ref('stg_channels') }}
),
districts as (
    select * from {{ ref('stg_districts') }}
),
departments as (
    select * from {{ ref('stg_departments') }}
),

joined as (

    select
        r.request_id,
        r.submitted_at,
        r.resolved_at,
        r.status,
        r.priority,
        r.resolution_hours,
        r.satisfaction_score,
        r.citizen_age_band,
        r.has_invalid_duration,
        r.has_impossible_timestamps,

        r.service_id,
        s.service_name,
        s.category                      as service_category,
        s.target_resolution_hours,

        r.channel_id,
        c.channel_name,
        c.is_digital,

        r.district_id,
        d.district_name,
        d.region,
        d.population,

        r.department_id,
        dp.department_name

    from requests r
    left join services    s  on r.service_id    = s.service_id
    left join channels    c  on r.channel_id    = c.channel_id
    left join districts   d  on r.district_id   = d.district_id
    left join departments dp on r.department_id = dp.department_id

)

select
    *,

    -- Calendar attributes. dow follows the Python convention used on Days 1 to 3
    -- (Monday = 0), which is isodow - 1 in Postgres, NOT extract(dow).
    extract(hour  from submitted_at)::int          as submitted_hour,
    (extract(isodow from submitted_at) - 1)::int   as submitted_dow,
    extract(month from submitted_at)::int          as submitted_month,
    date_trunc('month', submitted_at)::date        as submitted_month_start,
    case when extract(isodow from submitted_at) - 1 >= 5 then 1 else 0 end as is_weekend,

    case priority when 'Low' then 0 when 'Medium' then 1 when 'High' then 2 end as priority_rank,

    -- The single definition of the classification target used on Day 3.
    -- NULL where it is genuinely unknowable: an open request has not finished,
    -- and a nulled impossible duration cannot be judged against a target.
    case
        when status = 'Open'         then null
        when resolution_hours is null then null
        when resolution_hours <= target_resolution_hours then 1
        else 0
    end                                            as sla_met,

    {{ resolution_band('resolution_hours', 'target_resolution_hours') }} as resolution_band,

    -- Backlog view: a request that has not been resolved is still consuming capacity.
    case when status = 'Open' then 1 else 0 end    as is_open

from joined
