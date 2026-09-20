"""Gemini adapter unit tests (offline — no network, no key)."""
import json

from categories.invoices.adapters import gemini as gem
from core.harness.adapter_base import RawResult


def _raw_with_text(text: str) -> RawResult:
    return RawResult(payload={"candidates": [{"content": {"parts": [
        {"text": text}]}}]})


GOOD = json.dumps({
    "vendor_name": "Tokyo Office Supply K.K.",
    "vendor_tax_id": "T1234567890123",
    "invoice_number": "INV-2026-00417",
    "invoice_date": "2026-03-04",
    "due_date": "2026-04-30",
    "currency": "JPY",
    "subtotal": "120000",
    "tax_total": "12000",
    "total": "132000",
    "tax_rates": ["10"],
    "payment_account": None,
    "line_item_count": "6",
})


class TestToCanonical:
    def test_maps_fields_without_fixing_values(self):
        out = gem.GeminiAdapter(config={}).to_canonical(_raw_with_text(GOOD))
        assert out["invoice_date"] == "2026-03-04"
        assert out["total"] == "132000"
        assert out["payment_account"] is None
        # unit/label mapping only: string count -> int
        assert out["line_item_count"] == 6

    def test_bad_json_yields_empty(self):
        assert gem.GeminiAdapter(config={}).to_canonical(
            _raw_with_text("not json at all")) == {}

    def test_empty_candidates(self):
        assert gem.GeminiAdapter(config={}).to_canonical(
            RawResult(payload={})) == {}

    def test_non_dict_json(self):
        assert gem.GeminiAdapter(config={}).to_canonical(
            _raw_with_text("[1,2,3]")) == {}


class TestPrompt:
    def test_prompt_excludes_metadata_header(self):
        prompt = gem.load_prompt()
        assert "Extraction Prompt v1" not in prompt
        assert "vendor_name" in prompt
        assert "ISO 8601" in prompt


class TestModelSelection:
    def test_default_model(self):
        assert gem.GeminiAdapter(config={}).model == "gemini-3.8-flash"

    def test_model_from_config(self):
        assert gem.GeminiAdapter(config={
            "tool_models": {"google_gemini_flash": "gemini-2.5-pro"}}
        ).model == "gemini-2.5-pro"


class TestEstimate:
    def test_positive_and_tiny(self):
        from decimal import Decimal
        from pathlib import Path
        from core.harness.adapter_base import DocFile
        est = gem.GeminiAdapter(config={}).estimate_cost(
            DocFile("X", "clean_pdf", Path("f.pdf"), "0" * 64))
        assert est > 0 and est < Decimal("0.01")
