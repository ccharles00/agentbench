"""OpenAI + Textract adapter unit tests (offline — no network, no keys)."""
import json

import pytest

from categories.invoices.adapters import openai as oai
from categories.invoices.adapters import textract as tx
from core.harness.adapter_base import RawResult


def _oai_raw(text: str) -> RawResult:
    return RawResult(payload={"choices": [{"message": {"content": text}}]})


class TestOpenAI:
    def test_maps_fields(self):
        good = json.dumps({"vendor_name": "Acme", "total": "1234.56",
                           "line_item_count": "6", "payment_account": None})
        out = oai.OpenAIAdapter(config={}).to_canonical(_oai_raw(good))
        assert out["vendor_name"] == "Acme"
        assert out["line_item_count"] == 6
        assert out["payment_account"] is None

    def test_bad_json_empty(self):
        assert oai.OpenAIAdapter(config={}).to_canonical(_oai_raw("nope")) == {}

    def test_model_from_config(self):
        assert oai.OpenAIAdapter(config={
            "tool_models": {"openai_chat": "gpt-5.6-luna"}}).model == "gpt-5.6-luna"

    def test_estimate_positive(self):
        from decimal import Decimal
        from pathlib import Path
        from core.harness.adapter_base import DocFile
        est = oai.OpenAIAdapter(config={}).estimate_cost(
            DocFile("X", "clean_pdf", Path("f.pdf"), "0" * 64))
        assert Decimal("0.005") < est < Decimal("0.05")


def _tx_payload(fields: list[tuple[str, str]], n_line_items: int = 0,
                labels: dict[str, str] | None = None) -> dict:
    labels = labels or {}
    return {
        "DocumentMetadata": {"Pages": 1},
        "ExpenseDocuments": [{
            "SummaryFields": [
                {"Type": {"Text": t}, "ValueDetection": {"Text": v},
                 **({"LabelDetection": {"Text": labels[t]}} if t in labels else {})}
                for t, v in fields
            ],
            "LineItemGroups": ([{"LineItems": [{"LineItemList": [{"Type": {
                "Text": "ITEM"}, "ValueDetection": {"Text": "x"}}]}] * n_line_items}]
                if n_line_items else []),
        }],
    }


class TestTextract:
    def test_label_mapping(self):
        raw = RawResult(payload=_tx_payload([
            ("VENDOR_NAME", "Acme Ltd"),
            ("INVOICE_RECEIPT_ID", "INV-1"),
            ("TOTAL", "1234.56"),
            ("TAX", "56.20"),
            ("CURRENCY", "USD"),
            ("SOMETHING_ELSE", "ignored"),
        ], n_line_items=4))
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert out == {"vendor_name": "Acme Ltd", "invoice_number": "INV-1",
                       "total": "1234.56", "tax_total": "56.20",
                       "currency": "USD", "line_item_count": 4}

    def test_tax_rates_from_labels(self):
        # rates live in LabelDetection on TAX fields (DECISIONS #23)
        raw = RawResult(payload=_tx_payload(
            [("TAX", "56.20"), ("TAX", "7.00")],
            labels={"TAX": "USt 19% / USt (reduced) 7%"}))
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert out["tax_rates"] == ["19", "7"]

    def test_tax_rate_retention_excluded(self):
        raw = RawResult(payload=_tx_payload(
            [("TAX", "16.00"), ("TAX", "-10.00")],
            labels={"TAX": "IVA 16%"}))
        # second TAX field label contains 'reten' -> excluded (#18)
        raw.payload["ExpenseDocuments"][0]["SummaryFields"][1][
            "LabelDetection"] = {"Text": "ISR retenida (10%)"}
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert out["tax_rates"] == ["16"]

    def test_vendor_tax_id_priority(self):
        # VENDOR_VAT_NUMBER outranks a generic TAX_PAYER_ID
        raw = RawResult(payload=_tx_payload([
            ("TAX_PAYER_ID", "generic-1"),
            ("VENDOR_VAT_NUMBER", "DE123456789"),
        ]))
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert out["vendor_tax_id"] == "DE123456789"

    def test_currency_sibling_key_with_priority(self):
        # Currency sits on the SummaryField (sibling of ValueDetection);
        # TOTAL outranks SUBTOTAL and TAX when codes disagree
        payload = {
            "DocumentMetadata": {"Pages": 1},
            "ExpenseDocuments": [{"SummaryFields": [
                {"Type": {"Text": "TAX"}, "ValueDetection": {"Text": "1.00"},
                 "Currency": {"Code": "EUR"}},
                {"Type": {"Text": "SUBTOTAL"}, "ValueDetection": {"Text": "10.00"},
                 "Currency": {"Code": "EUR"}},
                {"Type": {"Text": "TOTAL"}, "ValueDetection": {"Text": "11.00"},
                 "Currency": {"Code": "USD"}},
            ]}],
        }
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(
            RawResult(payload=payload))
        assert out["currency"] == "USD"

    def test_currency_falls_back_when_total_lacks_it(self):
        payload = {
            "DocumentMetadata": {"Pages": 1},
            "ExpenseDocuments": [{"SummaryFields": [
                {"Type": {"Text": "TOTAL"}, "ValueDetection": {"Text": "11.00"}},
                {"Type": {"Text": "TAX"}, "ValueDetection": {"Text": "1.00"},
                 "Currency": {"Code": "JPY"}},
            ]}],
        }
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(
            RawResult(payload=payload))
        assert out["currency"] == "JPY"

    def test_values_untouched(self):
        # label mapping only — a German-formatted total must stay as returned
        raw = RawResult(payload=_tx_payload([("TOTAL", "1.234,56")]))
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert out["total"] == "1.234,56"

    def test_missing_fields_absent(self):
        raw = RawResult(payload=_tx_payload([("TOTAL", "10.00")]))
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert "currency" not in out and "payment_account" not in out
        assert "invoice_date" not in out

    def test_due_date_variants_first_wins(self):
        raw = RawResult(payload=_tx_payload([
            ("DUE_DATE", "2026-04-30"), ("PAYMENT_DUE_DATE", "other")]))
        out = tx.TextractAdapter.__new__(tx.TextractAdapter).to_canonical(raw)
        assert out["due_date"] == "2026-04-30"
