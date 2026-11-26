"""Publish the simulated event stream to Kafka/Redpanda.
   python simulator/produce_events.py --bootstrap localhost:19092 --file data/raw/events/events.jsonl"""
import argparse, json, time
from confluent_kafka import Producer

ap = argparse.ArgumentParser()
ap.add_argument("--bootstrap", default="localhost:19092"); ap.add_argument("--topic", default="orders.events")
ap.add_argument("--file", default="data/raw/events/events.jsonl")
ap.add_argument("--rate", type=int, default=0, help="events per second (0 = as fast as possible)")
a = ap.parse_args()
p = Producer({"bootstrap.servers": a.bootstrap})
n = 0
with open(a.file) as f:
    for line in f:
        key = json.loads(line).get("event_id") or ""
        p.produce(a.topic, key=key, value=line.strip())
        n += 1
        if n % 1000 == 0:
            p.poll(0)
        if a.rate:
            time.sleep(1 / a.rate)
p.flush()
print(f"published {n} events to {a.topic}")
