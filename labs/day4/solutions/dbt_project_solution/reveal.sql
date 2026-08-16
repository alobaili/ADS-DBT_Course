select service_name,
       sum(requests_within_sla) as met,
       sum(requests_judged)     as judged,
       round(100.0*sum(requests_within_sla)/sum(requests_judged),1) as sla_pct
from analytics_marts.mart_sla_performance
where service_name in ('Water Supply Fault','Road Maintenance')
group by service_name order by service_name;
