"""Anomaly detection on hourly event volume: Poisson-style z-score against the median for the same hour of day
(weekday and weekend separately), which stays stable with few weeks of history.
   python -m lakesense.ml.anomaly"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from ..db import get_runner


def detect(hourly: pd.DataFrame, z_thresh=4.0):
    s = hourly.set_index("hour_ts")["events"].astype(float)
    s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="h")).fillna(0.0)  # outage hours have no rows
    df = pd.DataFrame({"events": s}); df["hod"] = df.index.hour; df["weekend"] = df.index.dayofweek >= 5
    med = df.groupby(["weekend", "hod"])["events"].transform("median")
    df["z"] = (df["events"] - med) / np.sqrt(med.clip(lower=1.0))
    df["anomaly"] = df["z"].abs() > z_thresh
    df["kind"] = np.where(df["z"] > z_thresh, "spike", np.where(df["z"] < -z_thresh, "drop", ""))
    return df.reset_index().rename(columns={"index": "hour_ts"})


def evaluate(flags, manifest):
    truth = set(pd.to_datetime(manifest["anomaly_hours"]))
    found = set(flags.loc[flags["anomaly"], "hour_ts"])
    tp = len(truth & found)
    return {"injected_anomalies": len(truth), "flagged": len(found), "true_positives": tp,
            "recall": round(tp / max(len(truth), 1), 3), "precision": round(tp / max(len(found), 1), 3)}


def run(db=None, manifest_path="data/raw/_events_manifest.json", out_dir="outputs"):
    cols, rows = get_runner(db).query("select hour_ts, events from gold.fact_events_hourly order by 1")
    hourly = pd.DataFrame(rows, columns=cols); hourly["hour_ts"] = pd.to_datetime(hourly["hour_ts"])
    flags = detect(hourly)
    Path(out_dir).mkdir(exist_ok=True, parents=True)
    flags[flags["anomaly"]].to_csv(Path(out_dir) / "anomalies.csv", index=False)
    result = {"flagged": int(flags["anomaly"].sum())}
    if Path(manifest_path).exists():
        result = evaluate(flags, json.loads(Path(manifest_path).read_text()))
    (Path(out_dir) / "anomaly_results.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
