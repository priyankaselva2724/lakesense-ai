select i.order_id, i.item_no, o.customer_id, i.product_id, cast(o.order_ts as date) as date_key,
       i.quantity, i.price, round(cast(i.quantity * i.price as numeric), 2) as revenue
from {{ source('silver', 'order_items') }} i
join {{ source('silver', 'orders') }} o on o.order_id = i.order_id
