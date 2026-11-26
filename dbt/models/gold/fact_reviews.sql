select r.review_id, r.order_id, o.customer_id, cast(o.order_ts as date) as date_key, r.rating, r.review_text
from {{ source('silver', 'reviews') }} r
join {{ source('silver', 'orders') }} o on o.order_id = r.order_id
