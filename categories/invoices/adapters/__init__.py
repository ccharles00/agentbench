"""Vendor adapters for the invoices category (spec B3.2).

Adding a tool = one module in this package + an entry in REGISTRY. Each
adapter documents the vendor API docs URL and the date they were verified
(spec C3.4). No real adapters are registered yet — they arrive with the
owner's API keys (TODO_OWNER.md); the LLM baselines will live here too.
"""
from __future__ import annotations

REGISTRY: dict[str, type] = {}
