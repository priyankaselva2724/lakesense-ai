# Resume bullets (auto-filled from your own run)

- Built an end-to-end Bronze/Silver/Gold data platform in Python and DuckDB processing 1,958,645 simulated retail records (14.98 s end to end), with a star-schema Gold layer of 9 tables.
- Designed a data-quality framework of 10 automated rules; detected 9 of 9 injected fault types in raw data, reconciled 9 exactly, quarantined 360 bad records and verified zero residual violations after cleaning.
- Built a LightGBM demand forecast with rolling-origin backtesting: WAPE 0.3121 vs 0.4495 for a seasonal-naive baseline (30.6% relative difference).
- Implemented anomaly detection on the hourly event stream: recall 100% and precision 100% on injected spikes and outages.
- Added pytest tests, GitHub Actions CI and a Streamlit dashboard.
