"""Ground-truth data model (spec B2.5).

One JSON file per base invoice, shared by all degradation variants. Amounts
are decimal strings at the currency's minor-unit precision; dates are ISO
8601 Gregorian regardless of how the document renders them.
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


def _q(value: str) -> str:
    """Normalize a decimal string: strip trailing zeros but keep at least one digit."""
    d = Decimal(value)
    return format(d.normalize(), "f")


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
    rate_str: str          # contributes to ground truth tax_rates


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
    due_date: date
    currency: str
    tax_mode: str                       # exclusive | inclusive | reverse_charge
    subtotal_rows: list[tuple[str, str]]
    tax_lines: list[TaxLine]
    total_display: str
    items: list[LineItem]
    subtotal: Decimal                   # net, always
    tax_total: Decimal
    total: Decimal
    payment_account: str | None
    payment_terms_display: str | None
    account_display: str | None = None    # payment_account as printed (e.g. spaced IBAN)
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
        return [tl.rate_str for tl in self.tax_lines if tl.rate_str != "ret"]

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
                "due_date": self.due_date.isoformat(),
                "currency": self.currency,
                "subtotal": money.to_minor_string(self.subtotal, self.currency),
                "tax_total": money.to_minor_string(self.tax_total, self.currency),
                "total": money.to_minor_string(self.total, self.currency),
                "tax_rates": self.tax_rate_strings(),
                "payment_account": self.payment_account,
                "line_item_count": len(self.items),
            },
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
