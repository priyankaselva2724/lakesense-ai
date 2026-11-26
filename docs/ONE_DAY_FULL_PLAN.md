# Full-scope day plan (about 10-12 focused hours)

## What was verified and what was not (read this first)
| Part | Status |
|---|---|
| Simulator, Bronze/Silver/Gold in DuckDB, 10 quality rules | Tested: 28 automated tests passed |
| Spark Bronze/Silver jobs | Tested in Parquet mode; row counts identical to the DuckDB build |
| Spark Structured Streaming (de-dup, validation, watermark) | Tested with a file source; Kafka source is the same code path with `KAFKA_BOOTSTRAP` set |
| dbt Gold models, schema tests, incremental run | Tested on the DuckDB adapter (all tests pass, incremental re-run passes) |
| LightGBM forecast, anomaly detection | Tested |
| SQL guardrail, text-to-SQL harness, enrichment, DQ agent, catalog copilot, API | Tested with a fake LLM (no real API calls were made) |
| Docker Compose stack, Delta Lake format, MinIO (S3A), Redpanda, Postgres JDBC, dbt-postgres, Airflow runs, MLflow, Terraform | Written carefully but NOT run here: expect to fix small issues on your machine. The runbook has a troubleshooting table |
| Real LLM accuracy numbers | Not measured: you will measure them |

## Timeline
| Time | Task | Done when |
|---|---|---|
| 0:00-0:45 | Install Docker, Python, Java 17, Git. Unzip, create venv, `pip install -r requirements.txt`, `python -m pytest -q`, `make lite` | Tests pass, docs/RESULTS.md exists |
| 0:45-2:15 | Read the code in this order: simulate, bronze, silver, quality, gold, spark/*, dbt models, ml/*, ai/*. Explain each aloud | You can draw the architecture from memory |
| 2:15-4:00 | `docker compose up -d --build`; fix any startup issues using the troubleshooting table | `docker compose ps` all running; MinIO bucket `lake` exists |
| 4:00-6:00 | Run the step-by-step commands in docs/RUNBOOK.md section 2 | Delta tables in MinIO, silver and gold in Postgres, dbt tests green |
| 6:00-7:00 | Trigger the DAGs in Airflow; take screenshots of the graph view | Both DAGs show green |
| 7:00-8:30 | AI features with your API key: evaluate with ablation, enrich, dq_agent. Read the failures | `outputs/eval_results.json` exists |
| 8:30-9:30 | `python -m lakesense.report`, screenshots (Airflow, dbt lineage graph from `dbt docs serve`, Streamlit, MinIO) | docs/RESULTS.md and RESUME_BULLETS.md updated |
| 9:30-10:30 | GitHub: push, topics, pin, screenshots in README, CI green | Public repo with passing CI |
| 10:30-12:00 | Practise the 2-minute walkthrough and the interview questions in docs/RESUME_AND_GITHUB.md | You can explain every component without notes |

If Docker misbehaves, do not lose the day: finish `make lite` and the Spark tests, publish the repo, and fix the Docker part tomorrow. List only what you actually ran.
