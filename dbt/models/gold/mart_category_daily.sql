select f.date_key, p.category, count(distinct f.order_id) as orders, sum(f.quantity) as units, round(cast(sum(f.revenue) as numeric), 2) as revenue
from {{ ref('fact_order_items') }} f join {{ ref('dim_product') }} p on p.product_id = f.product_id
group by f.date_key, p.category
