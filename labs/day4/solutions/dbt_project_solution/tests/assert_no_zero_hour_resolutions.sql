-- A resolution taking zero hours is not possible. Day 1's Pandas rule nulled
-- negatives and the 9999 sentinels but let ten zeroes through, and every one of
-- them was then scored as "SLA met". This test makes that class of fault
-- impossible to ship again unnoticed.
select request_id, resolution_hours
from {{ ref('fct_service_requests') }}
where resolution_hours <= 0
