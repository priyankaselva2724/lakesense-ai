# Runbook: run the full stack

Needs Docker Desktop with at least 8 GB RAM assigned, and a good internet connection (first start downloads images and Spark packages: 10-20 minutes).

## 0. Quick check without Docker (5 minutes)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q          # needs Java 17+ for the Spark tests
make lite                    # DuckDB build + docs/RESULTS.md
```

## 1. Start the platform
```bash
cp .env.example .env         # add your ANTHROPIC_API_KEY (optional, for the LLM features)
docker compose up -d --build
docker compose ps            # everything should be "running"
```
Open: Airflow http://localhost:8080 (password: `docker compose logs airflow | grep -i password`), MinIO http://localhost:9001 (minioadmin / minioadmin), MLflow http://localhost:5000, Streamlit http://localhost:8501, API docs http://localhost:8000/docs.

## 2. Run the pipeline step by step (best for learning and debugging)
```bash
X="docker compose exec -T airflow bash -lc"
$X "cd /opt/lakesense && python -c \"from lakesense import simulate; simulate.generate('data/raw'); simulate.generate_events('data/raw')\""
$X "cd /opt/lakesense && python -m lakesense.spark.bronze_batch"
$X "cd /opt/lakesense && python -m lakesense.spark.silver_batch"          # quality gate + publish to Postgres
$X "cd /opt/lakesense && python simulator/produce_events.py --bootstrap redpanda:9092"
$X "cd /opt/lakesense && python -m lakesense.spark.stream_events"
$X "cd /opt/lakesense/dbt && /home/airflow/dbt_venv/bin/dbt build --profiles-dir . --project-dir ."
$X "cd /opt/lakesense/dbt && /home/airflow/dbt_venv/bin/dbt docs generate --profiles-dir . --project-dir ."
$X "cd /opt/lakesense && python -m lakesense.ml.forecast && python -m lakesense.ml.anomaly"
```
Then trigger the `lakesense_daily` DAG in the Airflow UI to see the same steps orchestrated (it works after the manual run has succeeded once).

## 3. AI features (needs ANTHROPIC_API_KEY)
```bash
$X "cd /opt/lakesense && python -m lakesense.ai.evaluate --ablation"
$X "cd /opt/lakesense && python -m lakesense.ai.enrich --n 200"
$X "cd /opt/lakesense && python -m lakesense.ai.dq_agent"
$X "cd /opt/lakesense && python -m lakesense.report"      # RESULTS.md + RESUME_BULLETS.md from YOUR numbers
```
Note: enrich and dq_agent in this build read the DuckDB lite warehouse; run `make lite` once first (or point them at Postgres, a good extension exercise).

## 4. Azure (optional, Tier B)
```bash
cd infra/terraform && terraform init && terraform apply -var prefix=yourname123
# ... when finished:
terraform destroy -var prefix=yourname123
```
Swap `LAKE_ROOT` to `abfss://...` and add the Azure Hadoop jars to use ADLS instead of MinIO (documented extension). Always destroy resources after a session to avoid charges.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Containers exit or hang | Give Docker 8 GB RAM; `docker compose logs <service>` |
| Spark "package not found" on first run | Ivy downloads jars on first use; wait, retry |
| `NoSuchBucket` | `docker compose up minio-init` again, then retry |
| Kafka connection refused | From your laptop use `localhost:19092`, inside containers `redpanda:9092` |
| Postgres role `llm_readonly` missing | The init script runs only on first start: `docker compose down -v` then up |
| Windows line-ending errors | `git config core.autocrlf input`, re-clone |
| Port already in use | Change the left side of the port mapping in docker-compose.yml |
