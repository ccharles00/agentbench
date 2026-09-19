"""Ground-truth data model (spec B2.5, as amended by DECISIONS.md #18-#20).

One JSON file per base invoice, shared by all degradation variants. Amounts
are decimal strings at the currency's minor-unit precision; dates are ISO
8601 Gregorian regardless of how the document renders them (null when the
document prints no such date, e.g. fapiao due dates).

`withholding_total` is taxes withheld by the buyer (ISR/IVA retention), kept
out of `tax_total` (charged taxes only) — unscored in v1. `unscored_fields`
lists (field)s printed on the document but excluded from scoring because the
schema has no normalized form for them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from . import money

GT_FIELDS = (
    "vendor_name", "vendor_tax_id", "invoice_number", "invoice_date", "due_date",
    "currency", "subtotal", "tax_total", "total", "tax_rates", "payment_account",
    "line_item_count",
)
# stored in ground truth `fields` but not scored (DECISIONS.md #18)
GT_META_FIELDS = ("withholding_total",)


@dataclass
class Vendor:
    name: str
    address_lines: list[str]
    tax_id_label: str | None = None
    tax_id_display: str | None = None
    tax_id: str | None = None  # normalized form stored in ground truth


@dataclass
class LineItem:
    description: str
    quantity: str          # as printed, e.g. "2" or "2.5"
    unit: str              # as printed
    unit_price: Decimal    # canonical unit price (gross when tax-inclusive)
    unit_price_display: str
    amount_display: str
    amount: Decimal        # canonical line amount (gross when tax-inclusive)
    tax_rate: Decimal | None
    tax_display: str | None = None   # as printed in the fapiao tax column


@dataclass
class TaxLine:
    label: str             # as printed, e.g. "VAT 19%"
    amount_display: str
    rate_str: str | None   # contributes to ground truth tax_rates; None = withholding


@dataclass
class Invoice:
    doc_id: str
    country: str
    language: list[str]
    script: list[str]
    dimensions: dict
    title: str
    labels: dict
    vendor: Vendor
    customer_name: str
    customer_address_lines: list[str]
    customer_tax_id_label: str | None
    customer_tax_id_display: str | None
    invoice_number: str
    invoice_date: date
    due_date: date | None
    currency: str
    tax_mode: str                       # exclusive | inclusive | reverse_charge
    subtotal_rows: list[tuple[str, str]]
    tax_lines: list[TaxLine]
    total_display: str
    items: list[LineItem]
    subtotal: Decimal                   # net, always
    tax_total: Decimal                  # charged taxes only (DECISIONS.md #18)
    total: Decimal
    payment_account: str | None
    payment_terms_display: str | None
    account_display: str | None = None    # payment_account as printed (e.g. spaced IBAN)
    withholding_total: Decimal | None = None   # ISR+IVA retention; None = no withholding
    withholding_lines: list = field(default_factory=list)
    unscored_fields: list = field(default_factory=list)   # DECISIONS.md #19
    bank_lines: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rendered_strings: dict = field(default_factory=dict)
    dual_currency_line: str | None = None
    amount_in_words: str | None = None
    words_label: str | None = None
    qr_payload: str | None = None
    logo_svg: str = ""
    logo_hue: int = 210
    template_style: str = "standard"    # or "fapiao"
    layout: str = "a"
    page_size: str = "A4"
    direction: str = "ltr"
    font_stack_css: str = "'Noto Sans', sans-serif"

    @property
    def template_id(self) -> str:
        return f"{self.country.lower()}_{self.layout}"

    def tax_rate_strings(self) -> list[str]:
        # charged-tax rates only; withholding lines carry rate_str None (#18)
        return [tl.rate_str for tl in self.tax_lines if tl.rate_str is not None]

    def to_ground_truth(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "country": self.country,
            "language": self.language,
            "script": self.script,
            "dimensions": self.dimensions,
            "fields": {
                "vendor_name": self.vendor.name,
                "vendor_tax_id": self.vendor.tax_id,
                "invoice_number": self.invoice_number,
                "invoice_date": self.invoice_date.isoformat(),
                "due_date": self.due_date.isoformat() if self.due_date else None,
                "currency": self.currency,
                "subtotal": money.to_minor_string(self.subtotal, self.currency),
                "tax_total": money.to_minor_string(self.tax_total, self.currency),
                "withholding_total": (
                    money.to_minor_string(self.withholding_total, self.currency)
                    if self.withholding_total is not None else None),
                "total": money.to_minor_string(self.total, self.currency),
                "tax_rates": self.tax_rate_strings(),
                "payment_account": self.payment_account,
                "line_item_count": len(self.items),
            },
            "unscored_fields": list(self.unscored_fields),
            "line_items": [
                {
                    "description": it.description,
                    "quantity": it.quantity,
                    "unit": it.unit,
                    "unit_price": money.to_minor_string(it.unit_price, self.currency),
                    "amount": money.to_minor_string(it.amount, self.currency),
                    "tax_rate": money.fmt_rate(it.tax_rate) if it.tax_rate is not None else None,
                }
                for it in self.items
            ],
            "rendered_strings": self.rendered_strings,
        }


def dump_ground_truth(gt: dict) -> str:
    """Deterministic serialization: byte-identical for identical content (B2.1)."""
    return json.dumps(gt, ensure_ascii=False, indent=2) + "\n"
