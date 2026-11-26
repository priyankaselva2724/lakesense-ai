"""Catalog copilot: answers 'what does this table/column mean?' using retrieval over the dbt model descriptions.
Retrieval is TF-IDF (no embedding service needed); the LLM only sees the retrieved chunks and must cite them."""
from pathlib import Path
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .llm import call_llm


def load_chunks(schema_yml="dbt/models/gold/schema.yml"):
    doc = yaml.safe_load(Path(schema_yml).read_text())
    chunks = []
    for m in doc["models"]:
        chunks.append({"id": f"gold.{m['name']}", "text": f"Table gold.{m['name']}: {m.get('description', '')}"})
        for c in m.get("columns", []):
            tests = ", ".join(t if isinstance(t, str) else list(t)[0] for t in c.get("tests", []))
            chunks.append({"id": f"gold.{m['name']}.{c['name']}",
                           "text": f"Column {c['name']} of gold.{m['name']}: {c.get('description', '')} Tests: {tests}"})
    return chunks


def retrieve(question, chunks, k=4):
    vec = TfidfVectorizer(stop_words="english").fit([c["text"] for c in chunks] + [question])
    sims = cosine_similarity(vec.transform([question]), vec.transform([c["text"] for c in chunks]))[0]
    return [chunks[i] for i in sims.argsort()[::-1][:k] if sims[i] > 0]


def answer(question, chunks, llm=call_llm):
    hits = retrieve(question, chunks)
    if not hits:
        return {"answer": "I could not find this in the data catalog.", "sources": []}
    ctx = "\n".join(f"[{h['id']}] {h['text']}" for h in hits)
    system = "Answer ONLY from the catalog excerpts. Cite the ids in square brackets. If the excerpts do not contain the answer, say so."
    text, _ = llm(system, f"Catalog excerpts:\n{ctx}\n\nQuestion: {question}", 400)
    return {"answer": text, "sources": [h["id"] for h in hits]}
