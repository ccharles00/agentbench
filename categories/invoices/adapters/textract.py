"""AWS Textract adapter — the first dedicated document-AI service (spec B3.2).

Uses AnalyzeExpense (purpose-built invoice/receipt analysis), NOT a prompt:
this is the "specialist vs. general LLM" comparison the benchmark exists to
show. boto3 reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION
from the environment (loaded from .env).

to_canonical is pure label mapping (B3.1): Textract's field Type.Text ->
our field names, values exactly as returned (ValueDetection.Text strings —
no date parsing, no number fixing, no currency inference). Fields Textract
does not return (tax_rates, payment_account) stay absent = null.

Vendor docs verified 2026-09-20 (spec C3.4):
- API: https://docs.aws.amazon.com/textract/latest/dg/API_AnalyzeExpense.html
  summary field types INVOICE_RECEIPT_ID, VENDOR_NAME, TOTAL, SUBTOTAL, TAX,
  TAX_PAYER_ID, INVOICE_RECEIPT_DATE, DUE_DATE, PAYMENT_DUE_DATE, CURRENCY;
  line items under LineItemGroups[].LineItems[]
- Pricing: https://aws.amazon.com/textract/pricing/
  Analyze Expense $0.01/page (first 1M pages/mo, US regions); free tier
  100 pages/month. Billed per page; page count from DocumentMetadata.Pages.
"""
from __future__ import annotations

import os
import time
from decimal import Decimal
from pathlib import Path

from core.harness.adapter_base import DocFile, RawResult, TransientError

PRICE_PER_PAGE = Decimal("0.01")     # us-east-1 tier 1, verified 2026-09-20
ASSUMED_PAGES = 2                    # estimate before the response is known

# Textract summary-field type -> canonical field (label mapping only)
FIELD_MAP = {
    "VENDOR_NAME": "vendor_name",
    "TAX_PAYER_ID": "vendor_tax_id",
    "INVOICE_RECEIPT_ID": "invoice_number",
    "INVOICE_RECEIPT_DATE": "invoice_date",
    "DUE_DATE": "due_date",
    "PAYMENT_DUE_DATE": "due_date",
    "CURRENCY": "currency",
    "SUBTOTAL": "subtotal",
    "TAX": "tax_total",
    "TOTAL": "total",
}

_TRANSIENT = ("ThrottlingException", "ServiceUnavailable", "InternalError",
              "ProvisionedThroughputExceededException", "RequestLimitExceeded")


class TextractAdapter:
    tool_id = "aws_textract_expense"
    display_name = "AWS Textract (AnalyzeExpense)"

    def __init__(self, config: dict | None = None):
        import boto3
        # boto3 reads AWS_DEFAULT_REGION; .env.example uses AWS_REGION
        region = (os.environ.get("AWS_REGION")
                  or os.environ.get("AWS_DEFAULT_REGION"))
        self._client = boto3.client("textract", region_name=region)

    def version(self) -> str:
        return "analyze_expense"

    def estimate_cost(self, doc: DocFile) -> Decimal:
        return (PRICE_PER_PAGE * ASSUMED_PAGES).quantize(Decimal("0.000001"))

    def extract(self, doc: DocFile) -> RawResult:
        t0 = time.perf_counter()
        try:
            response = self._extract(doc.path)
        except Exception as exc:                    # boto3 client errors
            if any(t in type(exc).__name__ for t in _TRANSIENT):
                raise TransientError(f"{type(exc).__name__}: {exc}") from exc
            raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc
        latency = (time.perf_counter() - t0) * 1000

        pages = (response.get("DocumentMetadata") or {}).get("Pages", 1)
        cost = PRICE_PER_PAGE * int(pages)
        return RawResult(payload=response, latency_ms=latency, cost_usd=cost)

    def _extract(self, path: Path) -> dict:
        """Sync AnalyzeExpense per file; multi-page PDFs are split into pages
        and merged (the async API requires S3, which we don't assume)."""
        if path.suffix.lower() != ".pdf":
            return self._client.analyze_expense(
                Document={"Bytes": path.read_bytes()})

        import pymupdf
        with pymupdf.open(path) as pdf:
            if len(pdf) == 1:
                return self._client.analyze_expense(
                    Document={"Bytes": path.read_bytes()})
            page_blobs = []
            for i in range(len(pdf)):
                single = pymupdf.open()
                single.insert_pdf(pdf, from_page=i, to_page=i)
                page_blobs.append(single.tobytes())
                single.close()

        responses = [self._client.analyze_expense(Document={"Bytes": b})
                     for b in page_blobs]
        return {
            "DocumentMetadata": {"Pages": len(page_blobs)},
            "ExpenseDocuments": [ed for r in responses
                                 for ed in r.get("ExpenseDocuments", [])],
        }

    def to_canonical(self, raw: RawResult) -> dict:
        out: dict = {}
        seen: set[str] = set()

        def put(canonical: str, value) -> None:
            if canonical and canonical not in seen and value is not None:
                out[canonical] = value
                seen.add(canonical)

        for expense in raw.payload.get("ExpenseDocuments", []):
            for field in expense.get("SummaryFields", []):
                ftype = ((field.get("Type") or {}).get("Text") or "").upper()
                label = ((field.get("LabelDetection") or {}).get("Text") or "").casefold()
                value = (field.get("ValueDetection") or {}).get("Text")
                if value is None:
                    continue
                put(FIELD_MAP.get(ftype), value)
                if ftype == "NAME":
                    # Textract often types both parties as NAME; the printed
                    # label says which is which (label mapping per B3.1)
                    if any(k in label for k in ("vendor", "seller", "supplier",
                                                "from", "remit")):
                        put("vendor_name", value)
            n_items = sum(len(group.get("LineItems", []))
                          for group in expense.get("LineItemGroups", []))
            if n_items and "line_item_count" not in out:
                out["line_item_count"] = n_items
        return out
