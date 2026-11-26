select date_trunc('hour', event_ts) as hour_ts, count(*) as events, round(cast(sum(amount) as numeric), 2) as revenue
from {{ source('silver', 'events') }}
group by 1
