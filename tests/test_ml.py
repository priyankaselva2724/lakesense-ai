import duckdb, pandas as pd
from lakesense import pipeline, simulate
from lakesense.ml import forecast, anomaly


def test_forecast_backtest_runs(tmp_path):
    pipeline.run(tmp_path, n_orders=15000)
    r = forecast.run(tmp_path / "data" / "warehouse.duckdb", out_dir=str(tmp_path / "out"))
    assert len(r["folds"]) >= 2 and r["wape_model"] > 0 and r["wape_seasonal_naive"] > 0


def test_anomaly_detection_finds_injected_hours(tmp_path):
    man = simulate.generate_events(tmp_path, days=14)
    ev = pd.read_json(tmp_path / "events" / "events.jsonl", lines=True).dropna(subset=["event_id"]).drop_duplicates("event_id")
    ev["hour_ts"] = pd.to_datetime(ev["event_ts"]).dt.floor("h")
    hourly = ev.groupby("hour_ts").size().rename("events").reset_index()
    res = anomaly.evaluate(anomaly.detect(hourly), man)
    assert res["recall"] >= 0.8 and res["precision"] >= 0.8


def test_dq_agent_validates_llm_output(tmp_path):
    import json
    from lakesense.ai import dq_agent
    rep = {"rules": [{"rule": "null_customer_id", "found_in_raw": 100, "residual_after_cleaning": 0},
                     {"rule": "ok_rule", "found_in_raw": 0, "residual_after_cleaning": 0}]}
    fake = lambda s, u, m=0: (json.dumps([{"rule": "null_customer_id", "severity": "high", "probable_cause": "Upstream form allows empty customer",
                                           "suggested_action": "Make customer_id mandatory at source"}]), {})
    inc, md = dq_agent.explain_incidents(rep, llm=fake)
    assert inc[0]["severity"] == "high" and "null_customer_id" in md
    bad = lambda s, u, m=0: (json.dumps([{"column": "x", "rule_type": "drop_table", "rationale": "x"},
                                         {"column": "a", "rule_type": "not_null", "rationale": "key"}]), {})
    out = dq_agent.propose_rules({"table": "silver.orders", "columns": {}}, llm=bad)
    assert len(out["rules"]) == 1 and out["rejected_invalid"] == 1 and out["status"] == "PENDING_HUMAN_APPROVAL"


def test_catalog_rag_retrieves_and_cites():
    from lakesense.ai import catalog_rag
    chunks = catalog_rag.load_chunks()
    fake = lambda s, u, m=0: ("Revenue is the sum of quantity x price [gold.fact_orders].", {})
    r = catalog_rag.answer("How is revenue defined for an order?", chunks, llm=fake)
    assert "gold.fact_orders" in r["sources"]
