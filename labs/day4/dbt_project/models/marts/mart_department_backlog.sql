/*
    LAB 2, STEP 4.  Business question 2: which departments are accumulating a
    backlog, and is it getting worse?
    Grain: one row per department per month.  Target: exactly 70 rows.

    Note what this model is built from: the open requests that Wednesday's
    machine learning discarded as unlabelled.
*/

-- TODO (a): start from int_department_month so quiet months survive.
-- TODO:     left join the monthly activity aggregated from int_requests_enriched.
-- TODO (b): add cumulative_backlog as a running total with a window function,
--           and backlog_added_change with lag().

select 1 as todo
