select product_id, category, price as list_price from {{ source('silver', 'products') }}
