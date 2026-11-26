"""Spark jobs run in plain-Parquet mode here; Docker runs the same code with Delta Lake on MinIO."""
import os, pytest
pytest.importorskip("pyspark")
from lakesense import simulate, pipeline
from lakesense.spark import bronze_batch, silver_batch
from lakesense.spark.session import get_spark


@pytest.fixture(scope="module")
def spark_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("spark")
    os.environ.update(LAKE_FORMAT="parquet", LAKE_ROOT=str(root / "lake"), RAW_DIR=str(root / "raw"),
                      SPARK_JAVA_OPENS=os.getenv("SPARK_JAVA_OPENS", "0"))
    manifest = simulate.generate(root / "raw", n_orders=6000)
    spark = get_spark("test")
    bronze_batch.run(spark)
    metrics, rep = silver_batch.run(spark, manifest, out_dir=str(root / "out"))
    duck_m, duck_q = pipeline.run(root / "duck", n_orders=6000)
    yield metrics, rep, duck_m, duck_q
    spark.stop()


def test_spark_detects_all_faults(spark_run):
    _, rep, _, _ = spark_run
    assert rep["summary"]["fault_types_detected"] == 9
    assert rep["summary"]["counts_exactly_reconciled"] == 9
    assert rep["summary"]["fixable_rules_clean_after_silver"]


def test_spark_matches_duckdb_row_counts(spark_run):
    metrics, _, duck_m, _ = spark_run
    for t in ["customers", "products", "orders", "order_items", "reviews"]:
        assert metrics["silver"][t] == duck_m["rows"]["silver"][t], t
    assert metrics["silver"]["quarantine"] == duck_m["rows"]["silver"]["quarantine"]


def test_streaming_events_dedup_and_validation(spark_run, tmp_path):
    import json
    from lakesense.spark import stream_events
    from lakesense.spark.session import get_spark, read_lake
    raw = tmp_path / "raw"
    man = simulate.generate_events(raw, days=10)
    os.environ["RAW_DIR"] = str(raw)
    spark = get_spark("stream_test")
    for q in stream_events.start(spark):
        q.awaitTermination()
    silver = read_lake(spark, "silver", "events")
    bronze = read_lake(spark, "bronze", "events")
    n_lines = sum(1 for _ in open(raw / "events" / "events.jsonl"))
    assert bronze.count() == n_lines
    assert silver.count() == silver.select("event_id").distinct().count()          # no duplicates left
    assert silver.count() == n_lines - man["duplicate_events"] - man["null_event_id"]  # exactly the injected faults removed
