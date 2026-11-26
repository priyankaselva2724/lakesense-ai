"""Gold layer: star schema (facts + dimensions) and business marts for BI and the AI assistant."""
STEPS = {
"dim_customer": "create or replace table gold.dim_customer as select customer_id, state, email_domain, created_date from silver.customers",
"dim_product": "create or replace table gold.dim_product as select product_id, category, price as list_price from silver.products",
"dim_date": """create or replace table gold.dim_date as
select cast(d as date) as date_key, year(d) as year, month(d) as month, day(d) as day,
       dayname(d) as weekday, isodow(d) in (6, 7) as is_weekend
from generate_series(timestamp '2025-01-01', timestamp '2026-12-31', interval 1 day) t(d)""",
"fact_order_items": """create or replace table gold.fact_order_items as
select i.order_id, i.item_no, o.customer_id, i.product_id, cast(o.order_ts as date) as date_key,
       i.quantity, i.price, round(i.quantity * i.price, 2) as revenue
from silver.order_items i join silver.orders o using (order_id)""",
"fact_orders": """create or replace table gold.fact_orders as
select o.order_id, o.customer_id, cast(o.order_ts as date) as date_key, o.status,
       count(i.item_no) as items, round(coalesce(sum(i.quantity * i.price), 0), 2) as revenue
from silver.orders o left join silver.order_items i using (order_id)
group by o.order_id, o.customer_id, o.order_ts, o.status""",
"fact_reviews": """create or replace table gold.fact_reviews as
select r.review_id, r.order_id, o.customer_id, cast(o.order_ts as date) as date_key, r.rating, r.review_text
from silver.reviews r join silver.orders o using (order_id)""",
"mart_daily_revenue": """create or replace table gold.mart_daily_revenue as
select date_key, count(*) as orders, round(sum(revenue), 2) as revenue from gold.fact_orders group by date_key order by date_key""",
"mart_category_daily": """create or replace table gold.mart_category_daily as
select f.date_key, p.category, count(distinct f.order_id) as orders, sum(f.quantity) as units, round(sum(f.revenue), 2) as revenue
from gold.fact_order_items f join gold.dim_product p using (product_id) group by f.date_key, p.category""",
"mart_category_revenue": """create or replace table gold.mart_category_revenue as
select p.category, count(distinct f.order_id) as orders, sum(f.quantity) as units, round(sum(f.revenue), 2) as revenue
from gold.fact_order_items f join gold.dim_product p using (product_id) group by p.category order by revenue desc""",
}


def build(con):
    con.execute("create schema if not exists gold")
    for sql in STEPS.values():
        con.execute(sql)
    return {t: con.execute(f"select count(*) from gold.{t}").fetchone()[0] for t in STEPS}
