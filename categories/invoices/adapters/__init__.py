"""Vendor adapters for the invoices category (spec B3.2).

Adding a tool = one module in this package + an entry in REGISTRY. Each
adapter documents the vendor API docs URL and the date they were verified
(spec C3.4).
"""
from __future__ import annotations

from .gemini import GeminiAdapter
from .openai import OpenAIAdapter
from .textract import TextractAdapter

REGISTRY: dict[str, type] = {
    GeminiAdapter.tool_id: GeminiAdapter,
    OpenAIAdapter.tool_id: OpenAIAdapter,
    TextractAdapter.tool_id: TextractAdapter,
}
