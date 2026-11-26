select date_key, count(*) as orders, round(cast(sum(revenue) as numeric), 2) as revenue
from {{ ref('fact_orders') }} group by date_key
