"""Metrics (spec B4.2): rates with 95% Wilson confidence intervals.

Wilson scores are shown next to every percentage so small samples can't be
overread (spec A7).
"""
from __future__ import annotations

import math


Z = 1.959963984540054   # 95%


def wilson(successes: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denom
    margin = (Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile (q in [0, 100]); 0.0 for empty input."""
    if not values:
        return 0.0
    vs = sorted(values)
    if len(vs) == 1:
        return vs[0]
    pos = (len(vs) - 1) * q / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return vs[int(pos)]
    return vs[lo] + (vs[hi] - vs[lo]) * (pos - lo)


def _rate(successes: int, n: int) -> dict:
    lo, hi = wilson(successes, n)
    return {
        "successes": successes, "count": n,
        "rate": round(successes / n, 4) if n else None,
        "wilson95": [round(lo, 4), round(hi, 4)],
    }


def summarize(comparisons: list[dict], docs: list[dict]) -> dict:
    """Build the B4.2 metric block.

    comparisons: rows from aggregate.score_document (one per scored field)
    docs: one row per (document, variant) with exact_match, cost_usd,
    latency_ms, error flags.
    """
    n_fields = len(comparisons)
    n_correct = sum(1 for c in comparisons if c["outcome"] == "correct")
    n_hallu = sum(1 for c in comparisons if c["outcome"] == "hallucination")
    n_docs = len(docs)
    n_exact = sum(1 for d in docs if d["exact_match"])
    n_failed = sum(1 for d in docs if d.get("error"))
    costs = [float(d["cost_usd"]) for d in docs if d.get("cost_usd") is not None]
    latencies = [float(d["latency_ms"]) for d in docs if d.get("latency_ms") is not None]
    total_cost = sum(costs)

    out = {
        "documents": _rate(n_exact, n_docs) | {"metric": "document_exact_match"},
        "field_accuracy": _rate(n_correct, n_fields) | {"metric": "field_accuracy"},
        "hallucination_rate": _rate(n_hallu, n_fields) | {"metric": "hallucination_rate"},
        "api_failure_rate": _rate(n_failed, n_docs) | {"metric": "api_failure_rate"},
        "mean_cost_per_doc_usd": round(total_cost / n_docs, 6) if n_docs else 0.0,
        "cost_per_correct_doc_usd": (round(total_cost / n_exact, 6)
                                     if n_exact else None),
        "latency_ms": {
            "p50": round(percentile(latencies, 50), 1),
            "p95": round(percentile(latencies, 95), 1),
        },
        "total_cost_usd": round(total_cost, 6),
    }
    return out
