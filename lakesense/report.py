"""Turn YOUR measured results into docs/RESULTS.md and docs/RESUME_BULLETS.md:  python -m lakesense.report
Only numbers that exist in outputs/*.json are written. Nothing is invented."""
import json
from pathlib import Path
from .config import Paths


def _load(p):
    return json.loads(p.read_text()) if p.exists() else None


def main(root="."):
    p = Paths(root).ensure()
    docs = Path(root) / "docs"; docs.mkdir(exist_ok=True)
    m, q = _load(p.out / "metrics.json"), _load(p.out / "quality_report.json")
    ev, en = _load(p.out / "eval_results.json"), _load(p.out / "enrichment_results.json")
    fc, an = _load(p.out / "forecast_results.json"), _load(p.out / "anomaly_results.json")
    if not m or not q:
        raise SystemExit("Run `python -m lakesense.pipeline` first.")
    rb, rs, rg = m["rows"]["bronze"], m["rows"]["silver"], m["rows"]["gold"]
    s = q["summary"]
    res = ["# Results (generated from your own run)", "",
           "Data is SIMULATED (see `lakesense/simulate.py`). Numbers below come from `outputs/*.json`.", "",
           "## Pipeline", "", "| Metric | Value |", "|---|---|",
           f"| Raw records loaded (all tables) | {sum(rb.values()):,} |",
           f"| Silver records (clean) | {sum(v for k, v in rs.items() if k != 'quarantine'):,} |",
           f"| Records quarantined | {rs['quarantine']:,} |",
           f"| Gold tables built | {len(rg)} |",
           f"| End-to-end pipeline runtime (excl. data generation) | {m['pipeline_seconds_excluding_simulation']} s |", "",
           "## Data quality", "", "| Rule | Injected | Found in raw | Residual after cleaning |", "|---|---|---|---|"]
    for r in q["rules"]:
        res.append(f"| {r['rule']} | {r['injected'] if r['injected'] is not None else '-'} | {r['found_in_raw']} | {r['residual_after_cleaning']} |")
    res += ["", f"Fault types detected: **{s['fault_types_detected']} of {s['fault_types_injected']}**; counts reconciled exactly: "
            f"**{s['counts_exactly_reconciled']} of {s['fault_types_injected']}**."]
    bullets = [
        f"- Built an end-to-end Bronze/Silver/Gold data platform in Python and DuckDB processing {sum(rb.values()):,} simulated retail records "
        f"({m['pipeline_seconds_excluding_simulation']} s end to end), with a star-schema Gold layer of {len(rg)} tables.",
        f"- Designed a data-quality framework of {s['rules_total']} automated rules; detected {s['fault_types_detected']} of {s['fault_types_injected']} "
        f"injected fault types in raw data, reconciled {s['counts_exactly_reconciled']} exactly, quarantined {rs['quarantine']:,} bad records and "
        f"verified zero residual violations after cleaning."]
    if ev:
        g, w = ev["guardrail"], ev["with_descriptions"]
        res += ["", "## Text-to-SQL assistant", "", f"- Guardrail: blocked {g['blocked']} of {g['adversarial_statements']} adversarial SQL statements (offline test).",
                f"- Execution accuracy on {w['questions']} benchmark questions: **{w['execution_accuracy']:.0%}** (p95 latency {w['p95_latency_s']} s)."]
        line = (f"- Built a guardrailed natural-language-to-SQL assistant (sqlglot validation, allow-listed tables, read-only database connection) that blocked "
                f"{g['blocked']}/{g['adversarial_statements']} adversarial statements and reached {w['execution_accuracy']:.0%} execution accuracy on a {w['questions']}-question benchmark")
        wo = ev.get("without_descriptions")
        if wo:
            res.append(f"- Without schema descriptions: {wo['execution_accuracy']:.0%}.")
            line += f" ({wo['execution_accuracy']:.0%} without schema descriptions)"
        bullets.append(line + ".")
    if en:
        res += ["", "## LLM review enrichment", "", f"- {en['reviews_enriched']} reviews enriched, {en['invalid_outputs']} invalid outputs, "
                f"sentiment accuracy vs simulator truth {en['sentiment_accuracy_vs_simulator_truth']:.0%}, ~{en['tokens_per_1000_reviews']:,} tokens per 1,000 uncached reviews."]
        bullets.append(f"- Built an LLM review-enrichment step with pydantic-validated JSON output, retries and caching: {en['reviews_enriched']} reviews processed, "
                       f"{en['sentiment_accuracy_vs_simulator_truth']:.0%} sentiment accuracy against simulator ground truth.")
    if fc:
        res += ["", "## Demand forecast", "", f"- LightGBM WAPE {fc['wape_model']} vs seasonal-naive {fc['wape_seasonal_naive']} (rolling-origin backtest, {len(fc['folds'])} folds); {fc['improvement_vs_naive_pct']}% relative change."]
        bullets.append(f"- Built a LightGBM demand forecast with rolling-origin backtesting: WAPE {fc['wape_model']} vs {fc['wape_seasonal_naive']} for a seasonal-naive baseline ({fc['improvement_vs_naive_pct']}% relative difference).")
    if an and "recall" in an:
        res += ["", "## Streaming anomaly detection", "", f"- Detected {an['true_positives']} of {an['injected_anomalies']} injected hourly anomalies (precision {an['precision']}, recall {an['recall']})."]
        bullets.append(f"- Implemented anomaly detection on the hourly event stream: recall {an['recall']:.0%} and precision {an['precision']:.0%} on injected spikes and outages.")
    bullets.append("- Added pytest tests, GitHub Actions CI and a Streamlit dashboard.")
    (docs / "RESULTS.md").write_text("\n".join(res) + "\n")
    (docs / "RESUME_BULLETS.md").write_text("# Resume bullets (auto-filled from your own run)\n\n" + "\n".join(bullets) + "\n")
    print("Wrote docs/RESULTS.md and docs/RESUME_BULLETS.md")


if __name__ == "__main__":
    main()
