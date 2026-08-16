-- Every department must appear in every month, or the backlog trend has holes.
select department_id, count(*) as months_present
from {{ ref('mart_department_backlog') }}
group by 1
having count(*) <> (select count(*) from {{ ref('int_date_spine') }})
