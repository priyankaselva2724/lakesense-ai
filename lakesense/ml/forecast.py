"""Demand forecasting: LightGBM vs a seasonal-naive baseline with rolling-origin backtesting.
   python -m lakesense.ml.forecast      (logs to MLflow when MLFLOW_TRACKING_URI is set)"""
import json, os
from pathlib import Path
import numpy as np, pandas as pd
from ..db import get_runner

HORIZON = 7
FEATS = ["lag_7", "lag_14", "lag_28", "roll_mean_7", "roll_mean_28", "dow", "month", "cat"]


def load_daily(db=None):
    cols, rows = get_runner(db).query("select date_key, category, revenue from gold.mart_category_daily order by 1, 2")
    df = pd.DataFrame(rows, columns=cols)
    df["date_key"] = pd.to_datetime(df["date_key"]); df["revenue"] = df["revenue"].astype(float)
    return df


def make_features(df):
    """Every feature at day t uses data up to t - HORIZON only, so a forecast made HORIZON days ahead is honest."""
    idx = pd.date_range(df["date_key"].min(), df["date_key"].max())
    out = []
    for cat, g in df.groupby("category"):
        s = g.set_index("date_key")["revenue"].reindex(idx).fillna(0.0)
        f = pd.DataFrame({"y": s})
        f["lag_7"], f["lag_14"], f["lag_28"] = s.shift(HORIZON), s.shift(14), s.shift(28)
        f["roll_mean_7"] = s.shift(HORIZON).rolling(7).mean(); f["roll_mean_28"] = s.shift(HORIZON).rolling(28).mean()
        f["dow"], f["month"], f["category"] = idx.dayofweek, idx.month, cat
        out.append(f.rename_axis("date").reset_index())
    f = pd.concat(out, ignore_index=True).dropna()
    f["cat"] = f["category"].astype("category").cat.codes
    return f


def wape(y, p):
    return float(np.abs(y - p).sum() / max(np.abs(y).sum(), 1e-9))


def backtest(feat, folds=3, fold_days=14):
    import lightgbm as lgb
    last = feat["date"].max()
    res = []
    for k in range(folds, 0, -1):
        test_start = last - pd.Timedelta(days=k * fold_days - 1)
        test_end = test_start + pd.Timedelta(days=fold_days - 1)
        tr = feat[feat["date"] < test_start - pd.Timedelta(days=HORIZON)]
        te = feat[(feat["date"] >= test_start) & (feat["date"] <= test_end)]
        if len(tr) < 100 or te.empty:
            continue
        m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=10, verbose=-1, random_state=0)
        m.fit(tr[FEATS], tr["y"])
        res.append({"fold": k, "test_start": str(test_start.date()), "wape_model": wape(te["y"].values, m.predict(te[FEATS])),
                    "wape_seasonal_naive": wape(te["y"].values, te["lag_7"].values)})
    return res


def run(db=None, out_dir="outputs"):
    feat = make_features(load_daily(db))
    folds = backtest(feat)
    summary = {"folds": folds, "wape_model": round(float(np.mean([f["wape_model"] for f in folds])), 4),
               "wape_seasonal_naive": round(float(np.mean([f["wape_seasonal_naive"] for f in folds])), 4)}
    summary["improvement_vs_naive_pct"] = round(100 * (1 - summary["wape_model"] / summary["wape_seasonal_naive"]), 1)
    Path(out_dir).mkdir(exist_ok=True, parents=True)
    (Path(out_dir) / "forecast_results.json").write_text(json.dumps(summary, indent=2))
    if os.getenv("MLFLOW_TRACKING_URI"):
        import mlflow
        mlflow.set_experiment("lakesense-forecast")
        with mlflow.start_run():
            mlflow.log_metrics({"wape_model": summary["wape_model"], "wape_seasonal_naive": summary["wape_seasonal_naive"]})
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
