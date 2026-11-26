# Results (generated from your own run)

Data is SIMULATED (see `lakesense/simulate.py`). Numbers below come from `outputs/*.json`.

## Pipeline

| Metric | Value |
|---|---|
| Raw records loaded (all tables) | 1,958,645 |
| Silver records (clean) | 1,957,652 |
| Records quarantined | 360 |
| Gold tables built | 9 |
| End-to-end pipeline runtime (excl. data generation) | 14.98 s |

## Data quality

| Rule | Injected | Found in raw | Residual after cleaning |
|---|---|---|---|
| duplicate_orders | 150 | 150 | 0 |
| null_customer_id | 100 | 100 | 0 |
| future_order_date | 70 | 70 | 0 |
| status_inconsistent | 200 | 200 | 0 |
| non_positive_price | 80 | 80 | 0 |
| orphan_items | 60 | 60 | 0 |
| invalid_email | 90 | 90 | 0 |
| rating_out_of_range | 50 | 50 | 0 |
| missing_day_gap | 1 | 1 | 1 |
| orders_have_customers | - | 0 | 0 |

Fault types detected: **9 of 9**; counts reconciled exactly: **9 of 9**.

## Demand forecast

- LightGBM WAPE 0.3121 vs seasonal-naive 0.4495 (rolling-origin backtest, 3 folds); 30.6% relative change.

## Streaming anomaly detection

- Detected 5 of 5 injected hourly anomalies (precision 1.0, recall 1.0).
