"""Run the whole platform:  python -m lakesense.pipeline"""
import argparse, json, time
from pathlib import Path
import duckdb
from . import bronze, silver, gold, quality, simulate
from .config import Paths


def run(root=".", n_orders=20000, seed=42, regenerate=True):
    p = Paths(root).ensure()
    t = {}
    tic = time.perf_counter()
    manifest = simulate.generate(p.raw, n_orders=n_orders, seed=seed) if regenerate else json.loads((p.raw / "_fault_manifest.json").read_text())
    t["simulate"] = time.perf_counter() - tic
    if p.db.exists():
        p.db.unlink()
    con = duckdb.connect(str(p.db))
    tic = time.perf_counter(); rows_b = bronze.build(con, p.raw); t["bronze"] = time.perf_counter() - tic
    qb = quality.run_layer(con, "bronze")
    tic = time.perf_counter(); rows_s, quarantine = silver.build(con); t["silver"] = time.perf_counter() - tic
    qs = quality.run_layer(con, "silver")
    tic = time.perf_counter(); rows_g = gold.build(con); t["gold"] = time.perf_counter() - tic
    con.close()
    qreport = quality.report(qb, qs, manifest)
    metrics = {"rows": {"bronze": rows_b, "silver": rows_s, "gold": rows_g},
               "quarantine_by_reason": quarantine,
               "runtime_seconds": {k: round(v, 2) for k, v in t.items()},
               "pipeline_seconds_excluding_simulation": round(sum(v for k, v in t.items() if k != "simulate"), 2)}
    (p.out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (p.out / "quality_report.json").write_text(json.dumps(qreport, indent=2))
    return metrics, qreport


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="."); ap.add_argument("--orders", type=int, default=20000)
    a = ap.parse_args()
    m, q = run(a.root, a.orders)
    print(json.dumps(m, indent=2)); print(json.dumps(q["summary"], indent=2))
