"""Thin LLM wrapper. Needs ANTHROPIC_API_KEY (pip install anthropic). Model override: LAKESENSE_MODEL."""
import os

DEFAULT_MODEL = "claude-haiku-5-5"


def call_llm(system: str, user: str, max_tokens: int = 600):
    """Returns (text, usage) where usage = {'input_tokens': int, 'output_tokens': int}."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY to use the LLM features (see README).")
    import anthropic
    client = anthropic.Anthropic()
    r = client.messages.create(model=os.environ.get("LAKESENSE_MODEL", DEFAULT_MODEL), max_tokens=max_tokens,
                               system=system, messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return text, {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
