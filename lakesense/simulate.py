"""Synthetic retail data generator with deliberately injected data faults.

The fault manifest records exactly how many faults of each type were injected, so the data-quality
layer can be scored objectively (faults caught vs. injected). All data is SIMULATED."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

CATS = ["electronics", "home", "fashion", "sports", "beauty", "toys", "books", "grocery"]
STATES = ["TN", "KA", "MH", "DL", "TG", "KL", "GJ", "WB", "UP", "RJ"]
FIRST = ["Asha", "Ravi", "Meena", "Karthik", "Divya", "Arun", "Priya", "Vikram", "Sneha", "Rahul", "Anita", "Suresh"]
LAST = ["Kumar", "Nair", "Reddy", "Iyer", "Singh", "Patel", "Sharma", "Das", "Menon", "Rao"]
DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "example.org"]
TEXT = {
    ("delivery", "positive"): ["Arrived earlier than expected, very happy with the delivery.", "Fast shipping and the courier was polite."],
    ("delivery", "negative"): ["The parcel arrived two weeks late and nobody updated me.", "Delivery was very slow and tracking never worked."],
    ("delivery", "neutral"): ["Delivery took about the usual time.", "The parcel came on the promised date, nothing special."],
    ("product_quality", "positive"): ["Excellent quality, exactly as described.", "The product feels premium and works perfectly."],
    ("product_quality", "negative"): ["The product broke after two days of use.", "Poor quality material, not as described."],
    ("product_quality", "neutral"): ["The product is okay, does the job.", "Average quality for the usual standard."],
    ("price", "positive"): ["Great value for the price.", "Very affordable and worth every rupee."],
    ("price", "negative"): ["Overpriced for what you get.", "Too expensive compared to other shops."],
    ("price", "neutral"): ["The price is fair, neither cheap nor expensive.", "Price was as expected."],
    ("seller", "positive"): ["The seller answered quickly and was very helpful.", "Great seller, would buy again."],
    ("seller", "negative"): ["The seller ignored my messages completely.", "Rude seller and no help with my issue."],
    ("seller", "neutral"): ["The seller replied after a day.", "Seller communication was fine."],
    ("packaging", "positive"): ["Packed very carefully, nothing damaged.", "Neat and secure packaging."],
    ("packaging", "negative"): ["The box was crushed and the item was scratched.", "Terrible packaging, items were loose inside."],
    ("packaging", "neutral"): ["Packaging was standard.", "The box was plain but intact."],
}
TOPICS = ["delivery", "product_quality", "price", "seller", "packaging"]


def _ts(rng, n, start="2025-01-01", end="2026-06-30"):
    s, e = pd.Timestamp(start).value // 10**9, pd.Timestamp(end).value // 10**9
    return pd.to_datetime(rng.integers(s, e, n), unit="s")


def generate(raw_dir, n_customers=2000, n_products=300, n_orders=20000, seed=42, inject_faults=True):
    rng = np.random.default_rng(seed)
    raw = Path(raw_dir); raw.mkdir(parents=True, exist_ok=True)
    fmt = "%Y-%m-%d %H:%M:%S"

    cust = pd.DataFrame({"customer_id": [f"C{i:05d}" for i in range(n_customers)]})
    f, l = rng.choice(FIRST, n_customers), rng.choice(LAST, n_customers)
    cust["name"] = [f"{a} {b}" for a, b in zip(f, l)]
    cust["email"] = [f"{a.lower()}.{b.lower()}{i}@{rng.choice(DOMAINS)}" for i, (a, b) in enumerate(zip(f, l))]
    cust["state"] = rng.choice(STATES, n_customers)
    cust["created_at"] = _ts(rng, n_customers, "2024-01-01", "2024-12-31").strftime(fmt)

    prod = pd.DataFrame({"product_id": [f"P{i:04d}" for i in range(n_products)],
                         "category": rng.choice(CATS, n_products),
                         "price": np.round(rng.lognormal(4.0, 0.7, n_products) + 5, 2)})

    ots = _ts(rng, n_orders)
    orders = pd.DataFrame({"order_id": [f"O{i:06d}" for i in range(n_orders)],
                           "customer_id": rng.choice(cust["customer_id"], n_orders),
                           "order_ts": ots,
                           "status": rng.choice(["delivered", "shipped", "processing", "cancelled"], n_orders, p=[.7, .1, .05, .15])})
    orders["updated_at"] = (orders["order_ts"] + pd.to_timedelta(rng.integers(1, 72, n_orders), unit="h"))

    n_items = rng.integers(1, 5, n_orders)
    items = pd.DataFrame({"order_id": np.repeat(orders["order_id"].values, n_items)})
    items["item_no"] = items.groupby("order_id").cumcount() + 1
    items["product_id"] = rng.choice(prod["product_id"], len(items))
    items["quantity"] = rng.integers(1, 4, len(items))
    items["price"] = items["product_id"].map(prod.set_index("product_id")["price"])

    manifest = {}
    if inject_faults:
        mid = pd.Timestamp("2025-10-15").date()  # missing-day outage: no orders for one day
        gone = set(orders.loc[orders["order_ts"].dt.date == mid, "order_id"])
        orders = orders[~orders["order_id"].isin(gone)].reset_index(drop=True)
        items = items[~items["order_id"].isin(gone)].reset_index(drop=True)
        manifest["missing_day"] = 1

    deliv = orders[orders["status"] == "delivered"].sample(frac=0.6, random_state=seed)
    sent = rng.choice(["positive", "neutral", "negative"], len(deliv), p=[.55, .15, .30])
    topic = rng.choice(TOPICS, len(deliv))
    rating = np.where(sent == "positive", rng.integers(4, 6, len(deliv)),
                      np.where(sent == "neutral", 3, rng.integers(1, 3, len(deliv))))
    reviews = pd.DataFrame({"review_id": [f"R{i:06d}" for i in range(len(deliv))], "order_id": deliv["order_id"].values,
                            "rating": rating,
                            "review_text": [rng.choice(TEXT[(t, s)]) for t, s in zip(topic, sent)]})
    truth = pd.DataFrame({"review_id": reviews["review_id"], "true_sentiment": sent, "true_topic": topic})

    if inject_faults:
        idx = rng.choice(len(orders), 520, replace=False)
        nul, fut, case, dup = idx[:100], idx[100:170], idx[170:370], idx[370:520]
        orders["order_ts"] = orders["order_ts"].dt.strftime(fmt)
        orders["updated_at"] = orders["updated_at"].dt.strftime(fmt)
        orders.loc[nul, "customer_id"] = np.nan
        orders.loc[fut, "order_ts"] = "2030-01-15 10:00:00"
        orders.loc[case, "status"] = [("  " + s) if k % 2 else s.upper() for k, s in enumerate(orders.loc[case, "status"])]
        orders = pd.concat([orders, orders.iloc[dup]], ignore_index=True)
        items.loc[rng.choice(len(items), 80, replace=False), "price"] = -9.99
        orphan = pd.DataFrame({"order_id": [f"OX{i:04d}" for i in range(60)], "item_no": 1,
                               "product_id": "P0001", "quantity": 1, "price": 10.0})
        items = pd.concat([items, orphan], ignore_index=True)
        reviews.loc[rng.choice(len(reviews), 50, replace=False), "rating"] = 9
        bad = rng.choice(len(cust), 90, replace=False)
        cust.loc[bad, "email"] = cust.loc[bad, "email"].str.replace("@", "_at_", regex=False)
        manifest.update({"duplicate_orders": 150, "null_customer_id": 100, "future_order_date": 70,
                         "status_inconsistent": 200, "negative_price": 80, "orphan_items": 60,
                         "bad_email": 90, "rating_out_of_range": 50})
    else:
        orders["order_ts"] = orders["order_ts"].dt.strftime(fmt)
        orders["updated_at"] = orders["updated_at"].dt.strftime(fmt)

    for name, df in [("customers", cust), ("products", prod), ("orders", orders), ("order_items", items),
                     ("reviews", reviews), ("_truth_reviews", truth)]:
        df.to_csv(raw / f"{name}.csv", index=False)
    (raw / "_fault_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def generate_events(raw_dir, days=14, seed=11, base_per_hour=30, inject_faults=True):
    """Order-event stream as JSON lines (also published to Kafka by simulator/produce_events.py).
    Faults: duplicate events, null ids, and hourly anomalies (spikes and outages) recorded in a manifest."""
    import json as _json
    rng = np.random.default_rng(seed)
    raw = Path(raw_dir); raw.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp("2026-05-01")
    hours = pd.date_range(start, periods=days * 24, freq="h")
    busy = [i for i in range(48, len(hours)) if 8 <= hours[i].hour <= 20]  # anomalies only in business hours
    spikes = sorted(rng.choice(busy, 3, replace=False).tolist())
    outages = sorted(rng.choice([h for h in busy if h not in spikes], 2, replace=False).tolist())
    rows, k = [], 0
    for hi, h in enumerate(hours):
        lam = base_per_hour * (1.4 if h.dayofweek >= 5 else 1.0) * (0.4 + 0.6 * np.sin(np.pi * (h.hour + 1) / 24) ** 2)
        if inject_faults and hi in spikes:
            lam *= 6
        n = 0 if (inject_faults and hi in outages) else rng.poisson(lam)
        for _ in range(n):
            k += 1
            rows.append({"event_id": f"E{k:07d}", "order_id": f"O{rng.integers(0, 10**6):06d}",
                         "customer_id": f"C{rng.integers(0, 2000):05d}", "category": str(rng.choice(CATS)),
                         "amount": round(float(rng.lognormal(4.2, 0.6)), 2), "event_type": "order_created",
                         "event_ts": (h + pd.Timedelta(seconds=int(rng.integers(0, 3600)))).strftime("%Y-%m-%dT%H:%M:%S")})
    manifest = {}
    if inject_faults:
        dups = rng.choice(len(rows), int(0.03 * len(rows)), replace=False)
        nulls = rng.choice([i for i in range(len(rows)) if i not in set(dups)], 40, replace=False)
        for i in nulls:
            rows[i]["event_id"] = None
        rows += [dict(rows[i]) for i in dups]
        manifest = {"duplicate_events": len(dups), "null_event_id": 40,
                    "anomaly_hours": [str(hours[i]) for i in spikes + outages],
                    "spike_hours": [str(hours[i]) for i in spikes], "outage_hours": [str(hours[i]) for i in outages]}
    rng.shuffle(rows)
    d = raw / "events"; d.mkdir(exist_ok=True)
    with open(d / "events.jsonl", "w") as f:
        for r in rows:
            f.write(_json.dumps(r) + "\n")
    (raw / "_events_manifest.json").write_text(_json.dumps(manifest, indent=2))
    return manifest
