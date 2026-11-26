import json
import pytest
from lakesense import pipeline
from lakesense.ai.guard import validate, UnsafeSQL
from lakesense.ai import evaluate, enrich, text_to_sql


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("proj")
    (root / "eval").mkdir()
    metrics, q = pipeline.run(root, n_orders=6000)
    return root, metrics, q


def test_all_injected_faults_detected_and_reconciled(built):
    _, _, q = built
    s = q["summary"]
    assert s["fault_types_detected"] == s["fault_types_injected"] == 9
    assert s["counts_exactly_reconciled"] == 9


def test_silver_is_clean(built):
    assert built[2]["summary"]["fixable_rules_clean_after_silver"]


def test_layers_reconcile(built):
    m = built[1]["rows"]
    assert m["gold"]["fact_orders"] == m["silver"]["orders"]
    assert m["gold"]["fact_order_items"] == m["silver"]["order_items"]
    assert m["silver"]["orders"] < m["bronze"]["orders"]


@pytest.mark.parametrize("sql", json.load(open("eval/adversarial_sql.json")))
def test_adversarial_sql_blocked(sql):
    with pytest.raises(UnsafeSQL):
        validate(sql)


def test_safe_sql_gets_limit():
    assert "LIMIT" in validate("select * from gold.fact_orders")


def test_golden_questions_run_and_harness_scores_perfect_with_oracle_llm(built):
    root, _, _ = built
    golden = {g["question"]: g["sql"] for g in json.load(open("eval/golden_questions.json"))}

    def oracle(system, user, max_tokens=600):
        q = user.split("Question: ")[-1]
        return f"```sql\n{golden[q]}\n```", {"input_tokens": 1, "output_tokens": 1}

    r = evaluate.run_benchmark(root / "data" / "warehouse.duckdb", llm=oracle)
    assert r["execution_accuracy"] == 1.0


def test_malicious_llm_output_is_blocked(built):
    root, _, _ = built
    evil = lambda s, u, m=600: ("```sql\nDROP TABLE gold.fact_orders\n```", {"input_tokens": 1, "output_tokens": 1})
    assert text_to_sql.ask("anything", root / "data" / "warehouse.duckdb", llm=evil)["status"] == "blocked"


def test_enrichment_with_fake_llm(built):
    root, _, _ = built
    import pandas as pd
    truth = pd.read_csv(root / "data" / "raw" / "_truth_reviews.csv")

    def fake(system, text, max_tokens=300):
        return json.dumps({"sentiment": "positive", "topics": ["other"], "summary_en": text[:50]}), {"input_tokens": 5, "output_tokens": 5}

    r = enrich.enrich(root, n=30, llm=fake)
    assert r["reviews_enriched"] == 30 and r["invalid_outputs"] == 0
