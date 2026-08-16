/*
    Business question 1: are we meeting our service-level agreements?
    Grain: one row per service per month.
*/

select
    submitted_month_start                                       as month_start,
    service_id,
    service_name,
    service_category,
    count(*)                                                    as requests,
    count(sla_met)                                              as requests_judged,
    sum(sla_met)                                                as requests_within_sla,
    round(avg(sla_met)::numeric, 4)                             as sla_met_rate,
    round(avg(resolution_hours)::numeric, 1)                    as mean_resolution_hours,
    round(percentile_cont(0.5) within group (order by resolution_hours)::numeric, 1)
                                                                as median_resolution_hours,
    round(avg(satisfaction_score)::numeric, 2)                  as mean_satisfaction,
    sum(is_open)                                                as still_open
from {{ ref('int_requests_enriched') }}
group by 1, 2, 3, 4
