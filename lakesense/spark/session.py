"""Spark session + lake paths. Everything is configured through environment variables so the same code runs
(1) in Docker with Delta Lake on MinIO, Kafka and Postgres, and (2) locally/in CI with plain Parquet."""
import os
from pathlib import Path

DELTA = "io.delta:delta-spark_2.12:3.2.0"
KAFKA = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"
HADOOP_AWS = "org.apache.hadoop:hadoop-aws:3.3.4"
AWS_BUNDLE = "com.amazonaws:aws-java-sdk-bundle:1.12.262"
POSTGRES = "org.postgresql:postgresql:42.7.3"
JAVA_OPENS = " ".join(f"--add-opens=java.base/{m}=ALL-UNNAMED" for m in (
    "java.lang", "java.nio", "sun.nio.ch", "java.util", "java.lang.invoke", "java.net", "java.io",
    "java.util.concurrent", "sun.util.calendar", "sun.security.action"))


def lake_format():
    return os.getenv("LAKE_FORMAT", "delta")  # delta | parquet


def lake_root():
    return os.getenv("LAKE_ROOT", "data/lake")


def lake_path(layer, table):
    return f"{lake_root().rstrip('/')}/{layer}/{table}"


def raw_dir():
    return os.getenv("RAW_DIR", "data/raw")


def get_spark(app="lakesense"):
    from pyspark.sql import SparkSession
    b = SparkSession.builder.appName(app).master(os.getenv("SPARK_MASTER", "local[2]"))
    pkgs = []
    if lake_format() == "delta":
        pkgs.append(DELTA)
        b = (b.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
              .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
    if lake_root().startswith("s3a://"):
        pkgs += [HADOOP_AWS, AWS_BUNDLE]
        b = (b.config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
              .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ROOT_USER", "minioadmin"))
              .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"))
              .config("spark.hadoop.fs.s3a.path.style.access", "true")
              .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
              .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem"))
    if os.getenv("KAFKA_BOOTSTRAP"):
        pkgs.append(KAFKA)
    if os.getenv("PG_JDBC_URL"):
        pkgs.append(POSTGRES)
    if pkgs:
        b = b.config("spark.jars.packages", ",".join(pkgs))
    if os.getenv("SPARK_JAVA_OPENS", "0") == "1":  # only needed for Java 21 (local testing)
        b = b.config("spark.driver.extraJavaOptions", JAVA_OPENS)
    b = b.config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "4")
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def write_lake(df, layer, table, mode="overwrite"):
    (df.write.format(lake_format()).mode(mode).save(lake_path(layer, table)))


def read_lake(spark, layer, table):
    return spark.read.format(lake_format()).load(lake_path(layer, table))
