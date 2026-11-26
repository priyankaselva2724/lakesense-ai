.PHONY: lite test full-up full-down report
lite:            ## no Docker needed: DuckDB build + report
	python -m lakesense.pipeline && python -m lakesense.report
test:
	python -m pytest -q
full-up:         ## the whole stack (Spark, Delta, MinIO, Redpanda, Airflow, dbt, Postgres, MLflow, Streamlit, API)
	docker compose up -d --build
full-down:
	docker compose down
report:
	python -m lakesense.report
