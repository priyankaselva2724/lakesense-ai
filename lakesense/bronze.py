"""Bronze layer: raw files loaded as-is (all text), plus lineage columns."""
from pathlib import Path


def build(con, raw_dir):
    con.execute("create schema if not exists bronze")
    counts = {}
    for f in sorted(Path(raw_dir).glob("*.csv")):
        if f.name.startswith("_"):  # simulator ground-truth files are not source data
            continue
        t = f.stem
        con.execute(f"""create or replace table bronze.{t} as
            select *, current_timestamp as ingested_at, '{f.name}' as source_file
            from read_csv_auto('{f.as_posix()}', all_varchar=true)""")
        counts[t] = con.execute(f"select count(*) from bronze.{t}").fetchone()[0]
    return counts
