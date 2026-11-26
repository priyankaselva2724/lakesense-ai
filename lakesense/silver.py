"""Silver layer: typed, de-duplicated, validated, PII-masked. Rejected rows go to a quarantine table."""
EMAIL_RE = "^[^@ ]+@[^@ ]+[.][A-Za-z]{2,}$"

STEPS = {
"customers": f"""
create or replace table silver.customers as
with d as (select *, row_number() over (partition by customer_id order by ingested_at desc) rn
           from bronze.customers where customer_id is not null),
c as (select customer_id, upper(trim(state)) as state, try_cast(created_at as timestamp) as created_at,
             lower(trim(email)) as email from d where rn = 1)
select customer_id, state, cast(created_at as date) as created_date,
       coalesce(regexp_matches(email, '{EMAIL_RE}'), false) as email_valid,
       case when regexp_matches(email, '{EMAIL_RE}') then md5(email) end as email_hash,
       case when regexp_matches(email, '{EMAIL_RE}') then split_part(email, '@', 2) end as email_domain
from c""",
"products": """
create or replace table silver.products as
select product_id, lower(trim(category)) as category, cast(price as double) as price
from bronze.products where try_cast(price as double) > 0""",
"orders": """
create or replace table silver.orders as
with d as (select *, row_number() over (partition by order_id
             order by try_cast(updated_at as timestamp) desc nulls last, ingested_at desc) rn
           from bronze.orders)
select order_id, customer_id, try_cast(order_ts as timestamp) as order_ts,
       lower(trim(status)) as status, try_cast(updated_at as timestamp) as updated_at
from d
where rn = 1 and customer_id is not null and trim(customer_id) <> ''
  and try_cast(order_ts as timestamp) is not null and try_cast(order_ts as timestamp) <= current_timestamp""",
"order_items": """
create or replace table silver.order_items as
select i.order_id, cast(i.item_no as integer) as item_no, i.product_id,
       cast(i.quantity as integer) as quantity, cast(i.price as double) as price
from bronze.order_items i join silver.orders o on o.order_id = i.order_id
where try_cast(i.price as double) > 0 and try_cast(i.quantity as integer) > 0""",
"reviews": """
create or replace table silver.reviews as
select r.review_id, r.order_id, cast(r.rating as integer) as rating, r.review_text
from bronze.reviews r join silver.orders o on o.order_id = r.order_id
where try_cast(r.rating as integer) between 1 and 5""",
"quarantine": """
create or replace table silver.quarantine as
select 'orders' as source_table, 'null_customer_id' as reason, order_id as key
  from bronze.orders where customer_id is null or trim(customer_id) = ''
union all select 'orders', 'invalid_or_future_order_ts', order_id from bronze.orders
  where try_cast(order_ts as timestamp) is null or try_cast(order_ts as timestamp) > current_timestamp
union all select 'order_items', 'non_positive_price_or_quantity', order_id || '-' || item_no from bronze.order_items
  where coalesce(try_cast(price as double), -1) <= 0 or coalesce(try_cast(quantity as integer), -1) <= 0
union all select 'order_items', 'orphan_order_reference', order_id || '-' || item_no from bronze.order_items i
  where not exists (select 1 from bronze.orders o where o.order_id = i.order_id)
union all select 'reviews', 'rating_out_of_range', review_id from bronze.reviews
  where try_cast(rating as integer) is null or try_cast(rating as integer) not between 1 and 5""",
}


def build(con):
    con.execute("create schema if not exists silver")
    for name, sql in STEPS.items():
        con.execute(sql)
    counts = {t: con.execute(f"select count(*) from silver.{t}").fetchone()[0] for t in STEPS}
    q = dict(con.execute("select reason, count(*) from silver.quarantine group by 1").fetchall())
    dup = con.execute("select count(*) - count(distinct order_id) from bronze.orders").fetchone()[0]
    q["duplicate_orders_removed"] = dup
    return counts, q
