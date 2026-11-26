import json
from fastapi.testclient import TestClient
from lakesense import pipeline


def test_api_endpoints(tmp_path, monkeypatch):
    pipeline.run(tmp_path, n_orders=3000)
    monkeypatch.setenv("LAKESENSE_OUT", str(tmp_path / "outputs"))
    monkeypatch.setenv("LAKESENSE_DUCKDB", str(tmp_path / "data" / "warehouse.duckdb"))
    monkeypatch.delenv("LAKESENSE_PG_DSN", raising=False)
    from api.main import app
    c = TestClient(app)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/quality").json()["summary"]["fault_types_detected"] == 9
    assert "rows" in c.get("/metrics").json()
    import lakesense.ai.text_to_sql as t
    monkeypatch.setattr(t, "call_llm", lambda *a, **k: ("```sql\nselect count(*) from gold.fact_orders\n```", {}), raising=False)
    from lakesense.ai.text_to_sql import ask
    r = ask("how many orders", llm=lambda *a, **k: ("```sql\nselect count(*) from gold.fact_orders\n```", {}))
    assert r["status"] == "ok" and r["rows"][0][0] > 0
