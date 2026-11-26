"""Read-only database access shared by the AI assistant, API and dashboard.
Lite mode: DuckDB file (opened read-only). Full mode: PostgreSQL with a read-only role (LAKESENSE_PG_DSN)."""
import os
from pathlib import Path


class DuckRunner:
    def __init__(self, path):
        self.path = str(path)

    def query(self, sql):
        import duckdb
        con = duckdb.connect(self.path, read_only=True)
        try:
            cur = con.execute(sql)
            return [d[0] for d in cur.description], cur.fetchall()
        finally:
            con.close()

    def schema_rows(self):
        return self.query("select table_name, column_name, data_type from information_schema.columns "
                          "where table_schema='gold' order by table_name, ordinal_position")[1]


class PgRunner:
    def __init__(self, dsn):
        self.dsn = dsn

    def query(self, sql):
        import psycopg2
        con = psycopg2.connect(self.dsn)
        try:
            con.set_session(readonly=True, autocommit=True)
            with con.cursor() as cur:
                cur.execute("set statement_timeout = 15000")
                cur.execute(sql)
                return [d[0] for d in cur.description], cur.fetchall()
        finally:
            con.close()

    def schema_rows(self):
        return self.query("select table_name, column_name, data_type from information_schema.columns "
                          "where table_schema='gold' order by table_name, ordinal_position")[1]


def get_runner(db=None):
    """Accepts a runner, a path to a DuckDB file, or None (env decides)."""
    if db is not None and hasattr(db, "query"):
        return db
    if db is not None:
        return DuckRunner(db)
    dsn = os.getenv("LAKESENSE_PG_DSN")
    return PgRunner(dsn) if dsn else DuckRunner(Path(os.getenv("LAKESENSE_DUCKDB", "data/warehouse.duckdb")))
