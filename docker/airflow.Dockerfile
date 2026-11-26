FROM apache/airflow:2.9.3-python3.11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless libgomp1 && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
USER airflow
# dbt lives in its own virtualenv so its dependencies never clash with Airflow's
RUN python -m venv /home/airflow/dbt_venv && /home/airflow/dbt_venv/bin/pip install --no-cache-dir dbt-postgres==1.8.2
COPY requirements-full.txt /tmp/requirements-full.txt
RUN pip install --no-cache-dir -r /tmp/requirements-full.txt
ENV PYTHONPATH=/opt/lakesense
