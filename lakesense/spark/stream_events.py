"""Structured Streaming: events -> Bronze (raw) and Silver (parsed, validated, de-duplicated within a watermark).
Source is Kafka/Redpanda when KAFKA_BOOTSTRAP is set, otherwise a folder of JSON-lines files (demo/CI).
Uses Trigger.AvailableNow so it processes everything available and stops (Airflow friendly).
   python -m lakesense.spark.stream_events [--continuous]"""
import argparse, os
from pyspark.sql import functions as F, types as T
from .session import get_spark, lake_path, lake_format, raw_dir

SCHEMA = T.StructType([T.StructField(n, T.StringType()) for n in ("event_id", "order_id", "customer_id", "category", "event_type", "event_ts")]
                      + [T.StructField("amount", T.DoubleType())])


def read_source(spark):
    if os.getenv("KAFKA_BOOTSTRAP"):
        return (spark.readStream.format("kafka").option("kafka.bootstrap.servers", os.environ["KAFKA_BOOTSTRAP"])
                .option("subscribe", os.getenv("KAFKA_TOPIC", "orders.events")).option("startingOffsets", "earliest").load()
                .select(F.col("value").cast("string").alias("value"), "topic", "partition", "offset", F.col("timestamp").alias("kafka_ts")))
    return spark.readStream.format("text").load(os.path.join(raw_dir(), "events"))


def to_bronze(stream):
    return stream.withColumn("ingested_at", F.current_timestamp())


def to_silver(stream):
    """Pure transformation (unit-testable on any streaming DataFrame with a `value` column)."""
    ev = (stream.select(F.from_json("value", SCHEMA).alias("e")).select("e.*")
                .withColumn("event_ts", F.to_timestamp("event_ts")))
    ok = ev.where(F.col("event_id").isNotNull() & F.col("event_ts").isNotNull() & (F.col("amount") > 0))
    return ok.withWatermark("event_ts", "30 days").dropDuplicatesWithinWatermark(["event_id"])


def start(spark, continuous=False):
    src = read_source(spark)
    trig = {"processingTime": "10 seconds"} if continuous else {"availableNow": True}
    fmt = lake_format()
    q1 = (to_bronze(src).writeStream.format(fmt).outputMode("append").trigger(**trig)
          .option("checkpointLocation", lake_path("_checkpoints", "bronze_events")).start(lake_path("bronze", "events")))
    q2 = (to_silver(src).writeStream.format(fmt).outputMode("append").trigger(**trig)
          .option("checkpointLocation", lake_path("_checkpoints", "silver_events")).start(lake_path("silver", "events")))
    return [q1, q2]


def publish_silver_events(spark):
    from .session import read_lake
    from .silver_batch import publish_postgres
    df = read_lake(spark, "silver", "events")
    if os.getenv("PG_JDBC_URL"):
        publish_postgres(df, "events")
    return df.count()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--continuous", action="store_true"); a = ap.parse_args()
    spark = get_spark("stream_events")
    qs = start(spark, a.continuous)
    for q in qs:
        q.awaitTermination()
    print("silver events:", publish_silver_events(spark))
