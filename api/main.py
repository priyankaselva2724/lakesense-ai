"""REST API:  uvicorn api.main:app --reload     (docs at /docs)"""
import json, os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="LakeSense AI API", version="1.0.0")


def _out():
    return Path(os.getenv("LAKESENSE_OUT", "outputs"))


def _read(name):
    p = _out() / name
    if not p.exists():
        raise HTTPException(503, f"{name} not found. Run the pipeline first.")
    return json.loads(p.read_text())


class Question(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return _read("metrics.json")


@app.get("/quality")
def quality():
    return _read("quality_report.json")


@app.post("/ask")
def ask_lakehouse(q: Question):
    from lakesense.ai.text_to_sql import ask
    r = ask(q.question, log_path=_out() / "query_log.jsonl")
    if r["status"] != "ok":
        raise HTTPException(400 if r["status"] == "blocked" else 502, r["error"])
    return {"sql": r["sql"], "columns": r["columns"], "rows": r["rows"][:200], "latency_s": r["latency_s"]}


@app.post("/catalog")
def catalog(q: Question):
    from lakesense.ai import catalog_rag
    return catalog_rag.answer(q.question, catalog_rag.load_chunks())
