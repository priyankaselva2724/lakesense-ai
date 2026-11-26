FROM python:3.11-slim
WORKDIR /opt/lakesense
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt
COPY . .
ENV PYTHONPATH=/opt/lakesense
