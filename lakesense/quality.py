"""Data-quality rules. The same rules run on raw (bronze) data to DETECT problems and on clean (silver)
data to PROVE they were fixed. Detection is scored against the simulator's fault manifest."""
from .silver import EMAIL_RE

RULES = [
    dict(id="duplicate_orders", fault="duplicate_orders", fixable=True,
         bronze="select count(*) - count(distinct order_id) from bronze.orders",
         silver="select count(*) - count(distinct order_id) from silver.orders"),
    dict(id="null_customer_id", fault="null_customer_id", fixable=True,
         bronze="select count(*) from bronze.orders where customer_id is null or trim(customer_id) = ''",
         silver="select count(*) from silver.orders where customer_id is null"),
    dict(id="future_order_date", fault="future_order_date", fixable=True,
         bronze="select count(*) from bronze.orders where try_cast(order_ts as timestamp) > current_timestamp",
         silver="select count(*) from silver.orders where order_ts > current_timestamp"),
    dict(id="status_inconsistent", fault="status_inconsistent", fixable=True,
         bronze="select count(*) from bronze.orders where status <> lower(trim(status))",
         silver="select count(*) from silver.orders where status <> lower(trim(status))"),
    dict(id="non_positive_price", fault="negative_price", fixable=True,
         bronze="select count(*) from bronze.order_items where try_cast(price as double) <= 0",
         silver="select count(*) from silver.order_items where price <= 0"),
    dict(id="orphan_items", fault="orphan_items", fixable=True,
         bronze="select count(*) from bronze.order_items i where not exists (select 1 from bronze.orders o where o.order_id = i.order_id)",
         silver="select count(*) from silver.order_items i where not exists (select 1 from silver.orders o where o.order_id = i.order_id)"),
    dict(id="invalid_email", fault="bad_email", fixable=True,
         bronze=f"select count(*) from bronze.customers where email is null or not regexp_matches(email, '{EMAIL_RE}')",
         silver="select count(*) from silver.customers where email_valid = false and email_hash is not null"),
    dict(id="rating_out_of_range", fault="rating_out_of_range", fixable=True,
         bronze="select count(*) from bronze.reviews where try_cast(rating as integer) is null or try_cast(rating as integer) not between 1 and 5",
         silver="select count(*) from silver.reviews where rating not between 1 and 5"),
    dict(id="missing_day_gap", fault="missing_day", fixable=False,
         bronze="""with d as (select cast(try_cast(order_ts as timestamp) as date) dt from bronze.orders
                   where try_cast(order_ts as timestamp) <= current_timestamp group by 1)
                   select cast(date_diff('day', min(dt), max(dt)) + 1 - count(*) as integer) from d""",
         silver="""with d as (select cast(order_ts as date) dt from silver.orders group by 1)
                   select cast(date_diff('day', min(dt), max(dt)) + 1 - count(*) as integer) from d"""),
    dict(id="orders_have_customers", fault=None, fixable=True,
         bronze="select 0",
         silver="select count(*) from silver.orders o where not exists (select 1 from silver.customers c where c.customer_id = o.customer_id)"),
]


def run_layer(con, layer):
    return {r["id"]: int(con.execute(r[layer]).fetchone()[0]) for r in RULES}


def report(bronze_counts, silver_counts, manifest):
    rows = []
    for r in RULES:
        injected = manifest.get(r["fault"]) if r["fault"] else None
        b, s = bronze_counts[r["id"]], silver_counts[r["id"]]
        rows.append({"rule": r["id"], "injected": injected, "found_in_raw": b,
                     "detected": bool(injected is not None and b > 0),
                     "exact_match": bool(injected is not None and b == injected),
                     "residual_after_cleaning": s, "fixable": r["fixable"]})
    inj = [x for x in rows if x["injected"] is not None]
    summary = {"fault_types_injected": len(inj),
               "fault_types_detected": sum(x["detected"] for x in inj),
               "counts_exactly_reconciled": sum(x["exact_match"] for x in inj),
               "fixable_rules_clean_after_silver": all(x["residual_after_cleaning"] == 0 for x in rows if x["fixable"]),
               "rules_total": len(rows)}
    return {"summary": summary, "rules": rows}
