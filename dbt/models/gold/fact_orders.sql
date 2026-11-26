{{ config(materialized='incremental', unique_key='order_id') }}
select o.order_id, o.customer_id, cast(o.order_ts as date) as date_key, o.status, o.updated_at,
       count(i.item_no) as items, round(cast(coalesce(sum(i.quantity * i.price), 0) as numeric), 2) as revenue
from {{ source('silver', 'orders') }} o
left join {{ source('silver', 'order_items') }} i on i.order_id = o.order_id
{% if is_incremental() %}
where o.updated_at > (select max(updated_at) from {{ this }})
{% endif %}
group by o.order_id, o.customer_id, o.order_ts, o.status, o.updated_at
