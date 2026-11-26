"""Benchmark the text-to-SQL assistant:  python -m lakesense.ai.evaluate [--ablation]
Needs ANTHROPIC_API_KEY. Also reports the offline guardrail test (no key needed)."""
import argparse, json
from ..config import Paths
from ..db import get_runner
from .guard import validate, UnsafeSQL
from .llm import call_llm
from .text_to_sql import ask


def _norm(rows):
    return sorted(tuple(round(v, 2) if isinstance(v, float) else v for v in r) for r in rows)


def guard_test(adv_path="eval/adversarial_sql.json"):
    bad = json.load(open(adv_path))
    blocked = 0
    for s in bad:
        try:
            validate(s)
        except UnsafeSQL:
            blocked += 1
    return {"adversarial_statements": len(bad), "blocked": blocked}


def run_benchmark(db_path, llm=call_llm, golden_path="eval/golden_questions.json", with_descriptions=True, log_path=None):
    golden = json.load(open(golden_path))
    runner = get_runner(db_path)
    passed, details, lat = 0, [], []
    for g in golden:
        expected = _norm(runner.query(g["sql"])[1])
        r = ask(g["question"], db_path, llm=llm, with_descriptions=with_descriptions, log_path=log_path)
        ok = r["status"] == "ok" and _norm(r["rows"]) == expected
        passed += ok; lat.append(r["latency_s"])
        details.append({"question": g["question"], "passed": ok, "status": r["status"], "generated_sql": r["sql"]})
    lat.sort()
    return {"questions": len(golden), "passed": passed, "execution_accuracy": round(passed / len(golden), 3),
            "p95_latency_s": lat[int(0.95 * (len(lat) - 1))], "with_schema_descriptions": with_descriptions,
            "details": details}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default="."); ap.add_argument("--ablation", action="store_true")
    a = ap.parse_args(); p = Paths(a.root).ensure()
    out = {"guardrail": guard_test(), "with_descriptions": run_benchmark(p.db, log_path=p.out / "query_log.jsonl")}
    if a.ablation:
        out["without_descriptions"] = run_benchmark(p.db, with_descriptions=False)
    (p.out / "eval_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: (v if k == "guardrail" else {x: y for x, y in v.items() if x != "details"}) for k, v in out.items()}, indent=2))
