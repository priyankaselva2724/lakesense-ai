# GitHub and resume: how to use this project honestly and effectively

## The rule
Write a tool on your resume only after you have run it successfully in this project. Every number comes from `docs/RESULTS.md`, which is generated from your own runs. The data is simulated; say so.

## GitHub checklist
- Repo name `lakesense-ai`, public. Description: End-to-end data platform: Spark, Delta Lake, Kafka, Airflow, dbt, quality gate, ML and guarded LLM assistants.
- Topics: data-engineering, pyspark, delta-lake, kafka, airflow, dbt, data-quality, llm, text-to-sql, mlflow, docker, terraform.
- Put the architecture diagram and 4 screenshots (Airflow graph, dbt lineage, Streamlit, MinIO) at the top of the README.
- Keep the green CI badge. Commit in small steps with clear messages. Never commit `.env` or data.
- Pin the repo. Add a short description to your profile README.

## Resume entry (fill with YOUR measured numbers; delete bullets for anything you did not run)
**LakeSense AI: Streaming Lakehouse Platform with Data Quality Gate and Guarded LLM Assistants | PySpark, Delta Lake, Kafka (Redpanda), Airflow, dbt, PostgreSQL, Docker, LightGBM, MLflow, LLM APIs | GitHub link**
- Built a Bronze/Silver/Gold lakehouse in PySpark and Delta Lake on object storage, with Spark Structured Streaming from Kafka (de-duplication within a watermark) and batch ingestion, orchestrated by Airflow and modelled with dbt ([N] models, [N] tests passing).
- Designed a data-quality framework of [N] rules that detected [x] of [y] injected fault types in raw data, quarantined [N] bad records and verified zero violations after cleaning; failures stop the pipeline (quality gate).
- Built a guardrailed natural-language-to-SQL assistant (sqlglot validation, allow-listed tables, read-only database role) that blocked [x]/[y] adversarial statements and reached [x]% execution accuracy on a [N]-question benchmark.
- Implemented LightGBM demand forecasting (WAPE [x] vs [y] seasonal-naive baseline) and hourly anomaly detection (recall [x]%, precision [x]%) tracked with MLflow.
- Added CI with GitHub Actions, pytest ([N] tests), Docker Compose deployment and Terraform for an Azure ADLS Gen2 data lake.
Auto-filled versions of these lines are written to `docs/RESUME_BULLETS.md`.

## Interview questions you must be able to answer
1. Walk me through the architecture. Why Delta Lake? Why Postgres for Gold instead of querying the lake?
2. How do you handle duplicate and late events? (watermark, `dropDuplicatesWithinWatermark`, idempotent writes, Trigger.AvailableNow)
3. What does your quality gate do when a rule fails? How did you measure detection? Limits of simulated faults?
4. Why dbt incremental models? What is `unique_key` for?
5. How do you stop an LLM from running harmful SQL? (validation, allow-list, read-only role, timeout, audit log, prompt-injection tests)
6. How did you measure the assistant, and which questions failed and why?
7. What would break at 100x volume and how would you change it? (partitioning, cluster Spark, Kafka partitions, dbt incremental, cost)
8. What would you change for production on Azure? (managed identity, Key Vault, private endpoints, monitoring, CI/CD to ADF/Databricks)
9. Your forecast beat or did not beat the naive baseline: why?
10. What are the limits of this project? (simulated data, small scale, single-node Spark, 20 benchmark questions)

## Known gaps (say them before an interviewer finds them)
- Data is simulated; real data has messier problems.
- Spark runs in local mode inside a container, not on a cluster.
- The SQL guard parses DuckDB dialect and the benchmark was designed on the DuckDB build; re-check generated SQL on Postgres.
- `enrich` and `dq_agent` default to the DuckDB lite warehouse.
