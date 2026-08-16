/*
    Business question 2: which departments are accumulating a backlog, and is it
    getting worse?

    Grain: one row per department per month, on a dense spine so quiet months
    appear as zero rather than vanishing.

    Note the deliberate contrast with the SLA mart. The SLA question can only be
    answered from requests that have finished. This question is mostly about the
    requests that have NOT finished, which are exactly the rows Day 3 discarded
    as unlabelled.
*/

with grid as (
    select * from {{ ref('int_department_month') }}
),

activity as (
    select
        department_id,
        submitted_month_start                 as month_start,
        count(*)                              as requests_opened,
        sum(is_open)                          as still_open,
        sum(case when status <> 'Open' then 1 else 0 end) as requests_closed
    from {{ ref('int_requests_enriched') }}
    group by 1, 2
),

joined as (
    select
        g.department_id,
        g.department_name,
        g.month_start,
        coalesce(a.requests_opened, 0) as requests_opened,
        coalesce(a.requests_closed, 0) as requests_closed,
        coalesce(a.still_open, 0)      as unresolved_opened_this_month
    from grid g
    left join activity a
        on g.department_id = a.department_id
       and g.month_start   = a.month_start
)

select
    department_id,
    department_name,
    month_start,
    requests_opened,
    requests_closed,
    unresolved_opened_this_month,

    -- The window function is the point of this model: a backlog is a running
    -- total, not a monthly count. Each row carries the cumulative unresolved
    -- position as at the end of that month.
    sum(unresolved_opened_this_month) over (
        partition by department_id
        order by month_start
        rows between unbounded preceding and current row
    ) as cumulative_backlog,

    -- Month-on-month movement, so "is it getting worse" is answerable directly.
    unresolved_opened_this_month - lag(unresolved_opened_this_month) over (
        partition by department_id order by month_start
    ) as backlog_added_change

from joined
