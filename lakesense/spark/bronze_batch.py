"""Bronze (batch): raw CSV -> lake table, all columns as text + lineage columns.
   python -m lakesense.spark.bronze_batch"""
from pathlib import Path
from pyspark.sql import functions as F
from .session import get_spark, raw_dir, write_lake


def run(spark=None):
    spark = spark or get_spark("bronze_batch")
    counts = {}
    for f in sorted(Path(raw_dir()).glob("*.csv")):
        if f.name.startswith("_"):
            continue
        df = (spark.read.option("header", True).option("inferSchema", False).csv(str(f))
                   .withColumn("ingested_at", F.current_timestamp()).withColumn("source_file", F.lit(f.name)))
        write_lake(df, "bronze", f.stem)
        counts[f.stem] = df.count()
    return counts


if __name__ == "__main__":
    print(run())
