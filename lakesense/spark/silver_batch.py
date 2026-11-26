"""Silver (batch): typed, de-duplicated, validated, PII-masked tables + quarantine, built with Spark SQL.
Runs the SAME data-quality rules as the DuckDB version (transpiled with sqlglot) on raw and clean data and
fails the run if any fixable rule still has violations (quality gate).   python -m lakesense.spark.silver_batch"""
import json, os, sys
from pathlib import Path
import sqlglot
from ..quality import RULES, report as quality_report
from ..silver import EMAIL_RE
from .session import get_spark, read_lake, write_lake

SQL = {
"customers": f"""
with d as (select *, row_number() over (partition by customer_id order by ingested_at desc) rn
           from bronze_customers where customer_id is not null),
c as (select customer_id, upper(trim(state)) as state, try_cast(created_at as timestamp) as created_at,
             lower(trim(email)) as email from d where rn = 1)
select customer_id, state, cast(created_at as date) as created_date,
       coalesce(email rlike '{EMAIL_RE}', false) as email_valid,
       case when email rlike '{EMAIL_RE}' then md5(email) end as email_hash,
       case when email rlike '{EMAIL_RE}' then split_part(email, '@', 2) end as email_domain
from c""",
"products": """
select product_id, lower(trim(category)) as category, cast(price as double) as price
from bronze_products where try_cast(price as double) > 0""",
"orders": """
with d as (select *, row_number() over (partition by order_id
             order by try_cast(updated_at as timestamp) desc nulls last, ingested_at desc) rn
           from bronze_orders)
select order_id, customer_id, try_cast(order_ts as timestamp) as order_ts,
       lower(trim(status)) as status, try_cast(updated_at as timestamp) as updated_at
from d
where rn = 1 and customer_id is not null and trim(customer_id) <> ''
  and try_cast(order_ts as timestamp) is not null and try_cast(order_ts as timestamp) <= current_timestamp()""",
"order_items": """
select i.order_id, cast(i.item_no as int) as item_no, i.product_id,
       cast(i.quantity as int) as quantity, cast(i.price as double) as price
from bronze_order_items i join silver_orders o on o.order_id = i.order_id
where try_cast(i.price as double) > 0 and try_cast(i.quantity as int) > 0""",
"reviews": """
select r.review_id, r.order_id, cast(r.rating as int) as rating, r.review_text
from bronze_reviews r join silver_orders o on o.order_id = r.order_id
where try_cast(r.rating as int) between 1 and 5""",
"quarantine": """
select 'orders' as source_table, 'null_customer_id' as reason, order_id as key
  from bronze_orders where customer_id is null or trim(customer_id) = ''
union all select 'orders', 'invalid_or_future_order_ts', order_id from bronze_orders
  where try_cast(order_ts as timestamp) is null or try_cast(order_ts as timestamp) > current_timestamp()
union all select 'order_items', 'non_positive_price_or_quantity', concat(order_id, '-', item_no) from bronze_order_items
  where coalesce(try_cast(price as double), -1) <= 0 or coalesce(try_cast(quantity as int), -1) <= 0
union all select 'order_items', 'orphan_order_reference', concat(order_id, '-', item_no) from bronze_order_items i
  where not exists (select 1 from bronze_orders o where o.order_id = i.order_id)
union all select 'reviews', 'rating_out_of_range', review_id from bronze_reviews
  where try_cast(rating as int) is null or try_cast(rating as int) not between 1 and 5""",
}
BRONZE = ["customers", "products", "orders", "order_items", "reviews"]


def spark_sql_for(rule_sql):
    s = rule_sql.replace("bronze.", "bronze_").replace("silver.", "silver_")
    return sqlglot.transpile(s, read="duckdb", write="spark")[0]


def run_rules(spark, layer):
    return {r["id"]: int(spark.sql(spark_sql_for(r[layer])).collect()[0][0]) for r in RULES}


def publish_postgres(df, table):
    (df.write.format("jdbc").option("url", os.environ["PG_JDBC_URL"]).option("dbtable", f"silver.{table}")
       .option("user", os.environ.get("PG_USER", "lakesense")).option("password", os.environ.get("PG_PASSWORD", "lakesense"))
       .option("driver", "org.postgresql.Driver").option("truncate", "true").mode("overwrite").save())


def run(spark=None, manifest=None, out_dir="outputs"):
    spark = spark or get_spark("silver_batch")
    for t in BRONZE:
        read_lake(spark, "bronze", t).createOrReplaceTempView(f"bronze_{t}")
    rows_b = {t: spark.table(f"bronze_{t}").count() for t in BRONZE}
    qb = run_rules(spark, "bronze")
    for t, sql in SQL.items():
        df = spark.sql(sql).cache()
        df.createOrReplaceTempView(f"silver_{t}")
        write_lake(df, "silver", t)
        if os.getenv("PG_JDBC_URL"):
            publish_postgres(df, t)
    rows_s = {t: spark.table(f"silver_{t}").count() for t in SQL}
    qs = run_rules(spark, "silver")
    quarantine = {r["reason"]: r["n"] for r in spark.sql("select reason, count(*) n from silver_quarantine group by 1").collect()}
    quarantine["duplicate_orders_removed"] = rows_b["orders"] - spark.sql("select count(distinct order_id) from bronze_orders").collect()[0][0]
    if manifest is None:
        mp = Path(os.getenv("RAW_DIR", "data/raw")) / "_fault_manifest.json"
        manifest = json.loads(mp.read_text()) if mp.exists() else {}
    rep = quality_report(qb, qs, manifest)
    Path(out_dir).mkdir(exist_ok=True, parents=True)
    (Path(out_dir) / "quality_report.json").write_text(json.dumps(rep, indent=2))
    return {"bronze": rows_b, "silver": rows_s, "quarantine": quarantine}, rep


if __name__ == "__main__":
    metrics, rep = run()
    print(json.dumps(metrics, indent=2)); print(json.dumps(rep["summary"], indent=2))
    if not rep["summary"]["fixable_rules_clean_after_silver"]:
        print("QUALITY GATE FAILED: fixable rules still have violations after cleaning"); sys.exit(1)
