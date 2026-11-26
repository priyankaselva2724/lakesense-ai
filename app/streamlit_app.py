"""Dashboard:  streamlit run app/streamlit_app.py
Works on the DuckDB lite build and on the full PostgreSQL stack (set LAKESENSE_PG_DSN)."""
import json, os
from pathlib import Path
import pandas as pd, streamlit as st
from lakesense.db import get_runner

OUT = Path(os.getenv("LAKESENSE_OUT", "outputs"))
st.set_page_config(page_title="LakeSense AI", layout="wide")
st.title("LakeSense AI")
st.caption("Retail data platform on SIMULATED data: Bronze/Silver/Gold lakehouse, quality gate, streaming, ML and AI assistants.")
if not (OUT / "metrics.json").exists() and not (OUT / "quality_report.json").exists():
    st.warning("Run the pipeline first (see README)."); st.stop()
runner = get_runner()


def q(sql):
    cols, rows = runner.query(sql)
    return pd.DataFrame(rows, columns=cols)


def load(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else None


tabs = st.tabs(["Overview", "Data quality", "Business", "Streaming and anomalies", "Forecast", "Ask the Lakehouse", "Catalog copilot"])
m, qr = load("metrics.json"), load("quality_report.json")

with tabs[0]:
    if m:
        c = st.columns(3)
        c[0].metric("Raw records", f"{sum(m['rows']['bronze'].values()):,}")
        c[1].metric("Quarantined", f"{m['rows']['silver'].get('quarantine', 0):,}")
        c[2].metric("Pipeline seconds", m.get("pipeline_seconds_excluding_simulation", "-"))
        st.bar_chart(pd.Series(m["quarantine_by_reason"]))
    else:
        st.info("metrics.json not found (written by the lite pipeline).")
with tabs[1]:
    if qr:
        s = qr["summary"]
        st.metric("Injected fault types detected", f"{s['fault_types_detected']} / {s['fault_types_injected']}")
        st.dataframe(pd.DataFrame(qr["rules"]), use_container_width=True)
    inc = OUT / "incident_report.md"
    if inc.exists():
        st.markdown(inc.read_text())
with tabs[2]:
    st.line_chart(q("select date_key, revenue from gold.mart_daily_revenue order by 1").set_index("date_key"))
    st.bar_chart(q("select category, revenue from gold.mart_category_revenue").set_index("category"))
with tabs[3]:
    try:
        ev = q("select hour_ts, events from gold.fact_events_hourly order by 1").set_index("hour_ts")
        st.line_chart(ev)
        an = OUT / "anomalies.csv"
        if an.exists():
            st.subheader("Flagged hours"); st.dataframe(pd.read_csv(an))
        r = load("anomaly_results.json")
        if r:
            st.json(r)
    except Exception as e:
        st.info(f"Event data not available yet: {e}")
with tabs[4]:
    r = load("forecast_results.json")
    if r:
        st.metric("WAPE (LightGBM)", r["wape_model"]); st.metric("WAPE (seasonal naive)", r["wape_seasonal_naive"])
        st.dataframe(pd.DataFrame(r["folds"]))
    else:
        st.info("Run `python -m lakesense.ml.forecast`.")
with tabs[5]:
    question = st.text_input("Ask a business question", "Which 5 product categories have the highest revenue?")
    if st.button("Ask") and question:
        from lakesense.ai.text_to_sql import ask
        try:
            r = ask(question, log_path=OUT / "query_log.jsonl")
            st.code(r["sql"] or "", language="sql")
            st.dataframe(pd.DataFrame(r["rows"], columns=r["columns"])) if r["status"] == "ok" else st.error(f"{r['status']}: {r['error']}")
        except Exception as e:
            st.error(str(e))
with tabs[6]:
    cq = st.text_input("Ask about the data catalog", "How is revenue defined for an order?")
    if st.button("Search catalog") and cq:
        from lakesense.ai import catalog_rag
        try:
            a = catalog_rag.answer(cq, catalog_rag.load_chunks()); st.write(a["answer"]); st.caption("Sources: " + ", ".join(a["sources"]))
        except Exception as e:
            st.error(str(e))
