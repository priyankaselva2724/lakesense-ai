"""SQL guardrail: only a single read-only SELECT over allow-listed gold tables is allowed."""
import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"fact_orders", "fact_order_items", "fact_reviews", "dim_customer", "dim_product",
                  "dim_date", "mart_daily_revenue", "mart_category_revenue", "mart_category_daily",
                  "fact_events_hourly"}


class UnsafeSQL(ValueError):
    pass


def validate(sql: str, limit: int = 1000) -> str:
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except Exception as e:  # unparsable SQL is rejected, never executed
        raise UnsafeSQL(f"Could not parse SQL: {e}")
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeSQL("Exactly one statement is allowed")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise UnsafeSQL("Only SELECT statements are allowed")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command, exp.Copy)
    if any(tree.find(f) for f in forbidden):
        raise UnsafeSQL("Data-changing statements are not allowed")
    ctes = {c.alias for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        if t.name in ctes and not t.db:
            continue
        if t.db.lower() != "gold" or t.name.lower() not in ALLOWED_TABLES:
            raise UnsafeSQL(f"Table not allowed: {t.sql()}")
    if isinstance(tree, exp.Select) and not tree.args.get("limit"):
        tree = tree.limit(limit)
    return tree.sql(dialect="duckdb")
