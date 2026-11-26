"""Daily batch DAG: simulate -> Bronze -> Silver (+quality gate, publish to Postgres) -> dbt Gold -> ML -> AI reports.
Streaming events are processed by lakesense_events (Trigger.AvailableNow) so every run is finite and retry-safe."""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULTS = {"owner": "data-eng", "retries": 2, "retry_delay": timedelta(minutes=2)}
APP = "cd /opt/lakesense && "
DBT = "cd /opt/lakesense/dbt && /home/airflow/dbt_venv/bin/dbt"

with DAG("lakesense_daily", start_date=datetime(2026, 1, 1), schedule="@daily", catchup=False,
         default_args=DEFAULTS, tags=["lakesense"]) as daily:
    simulate = BashOperator(task_id="simulate_source_files",
                            bash_command=APP + "python -c \"from lakesense import simulate; simulate.generate('data/raw'); simulate.generate_events('data/raw')\"")
    produce = BashOperator(task_id="publish_events_to_kafka", bash_command=APP + "python simulator/produce_events.py --bootstrap redpanda:9092")
    stream = BashOperator(task_id="stream_events_to_lake", bash_command=APP + "python -m lakesense.spark.stream_events")
    bronze = BashOperator(task_id="bronze_batch", bash_command=APP + "python -m lakesense.spark.bronze_batch")
    silver = BashOperator(task_id="silver_batch_quality_gate", bash_command=APP + "python -m lakesense.spark.silver_batch")
    dbt_build = BashOperator(task_id="dbt_build_gold", bash_command=DBT + " build --profiles-dir . --project-dir .")
    dbt_docs = BashOperator(task_id="dbt_docs", bash_command=DBT + " docs generate --profiles-dir . --project-dir .")
    forecast = BashOperator(task_id="demand_forecast", bash_command=APP + "python -m lakesense.ml.forecast")
    anomalies = BashOperator(task_id="event_anomaly_detection", bash_command=APP + "python -m lakesense.ml.anomaly")
    simulate >> bronze >> silver >> dbt_build
    simulate >> produce >> stream >> dbt_build
    dbt_build >> [dbt_docs, forecast, anomalies]

with DAG("lakesense_events", start_date=datetime(2026, 1, 1), schedule="@hourly", catchup=False,
         default_args=DEFAULTS, tags=["lakesense", "streaming"]) as events:
    stream = BashOperator(task_id="stream_events_available_now", bash_command=APP + "python -m lakesense.spark.stream_events")
