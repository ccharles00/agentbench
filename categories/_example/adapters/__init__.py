"""Fake adapter for the _example stub (spec B0).

Deterministic behavior across the three tasks: doc 1 fully correct,
doc 2 with a wrong count, doc 3 hallucinating a count the truth holds null.
"""
from __future__ import annotations

from decimal import Decimal

from core.harness.adapter_base import DocFile, RawResult


class FakeAdapter:
    tool_id = "fake_extractor"
    display_name = "Fake Extractor (test stub)"

    def version(self) -> str:
        return "1.0.0"

    def estimate_cost(self, doc: DocFile) -> Decimal:
        return Decimal("0")

    def extract(self, doc: DocFile) -> RawResult:
        return RawResult(payload={"doc_id": doc.doc_id}, latency_ms=1.5)

    def to_canonical(self, raw: RawResult) -> dict:
        doc_id = raw.payload["doc_id"]
        if doc_id == "EX-0001":
            return {"widget_id": "wdg-001", "count": 3}      # correct (identifier normalizes)
        if doc_id == "EX-0002":
            return {"widget_id": "WDG-002", "count": 6}      # wrong count
        return {"widget_id": "WDG-003", "count": 5}          # hallucinated count


REGISTRY = {"fake_extractor": FakeAdapter}
