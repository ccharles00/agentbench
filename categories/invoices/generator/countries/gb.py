"""GB invoices: VAT 20%, DD/MM dates, IBAN accounts."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec


def _tax_id(rng: random.Random, name: str) -> tuple[str, str]:
    digits = ids.random_digits(rng, 9)
    return f"GB {digits[:3]} {digits[3:7]} {digits[7:]}", f"GB{digits}"


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"INV/{d.year}/{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def make_scenarios(cfg) -> dict:
    rate = Decimal(str(cfg[0]))  # [20]
    return {"vat20": {"mode": "exclusive", "rates": [rate]}}


SPEC = CountrySpec(
    code="GB", name="United Kingdom", currency="GBP",
    native_lang="en", scripts=("Latn",), font_stack=("Noto Sans",),
    numeric_dates=True,
    tax_label="VAT",
    vendors=(
        "Whitmore & Sons Ltd", "Northern Textiles Ltd", "Camden Print Works Ltd",
        "Thames Logistics Ltd", "Bakewell Foods Wholesalers Ltd", "Cotswold IT Services Ltd",
        "Kingsway Office Supplies Ltd", "Harbour Marine Engineering Ltd",
    ),
    customers=(
        "Ashfield Manufacturing Ltd", "Riverside Retail Group Ltd", "Pemberton Consulting Ltd",
        "Hallam Components Ltd", "Westbury Facilities Ltd", "Greystone Media Ltd",
    ),
    vendor_addresses=(
        ("14 Whitmore Street", "London EC1A 4JQ"),
        ("32 Victoria Road", "Leeds LS1 4BX"),
        ("Unit 5, Camden Lock Place", "London NW1 8AF"),
        ("9 Quayside", "Newcastle upon Tyne NE1 3TG"),
        ("18 Church Lane", "Sheffield S1 2GN"),
    ),
    customer_addresses=(
        ("7 Chandler Way", "Manchester M2 4WB"),
        ("45 Princes Street", "Edinburgh EH2 2BY"),
        ("22 Bridge Street", "Birmingham B2 4QP"),
        ("3 Regent Court", "Bristol BS1 6ED"),
    ),
    customer_tax_label="VAT No.",
    labels={"title": "TAX INVOICE", "tax_id_label": "VAT No.", "payment_account": "IBAN",
            "invoice_no": "Invoice No.", "subtotal": "Subtotal", "total": "Total"},
    title_en="TAX INVOICE",
    tax_id_label_en="VAT No.",
    descriptions=(
        "Office chairs, mesh back (pack of 4)",
        "Website maintenance retainer — monthly, includes hosting and minor updates",
        "Courier — next day service, 12 parcels",
        "Accounting services — quarterly VAT return preparation",
        "LED panel lights 600x600 (carton of 20)",
        "Server hosting — rack unit, monthly, includes remote hands",
        "Translation — EN to DE, technical manual, 60 pages",
        "Safety audit — warehouse, on-site, full report",
        "Packaging film roll 500mm x 300m",
        "Marketing consulting — half day, includes campaign review and written recommendations",
        "Oak plywood sheets 18mm, 2440x1220 (pack of 10)",
        "Staff training — manual handling, half day session",
    ),
    units=(("pcs", "pcs"), ("items", "items"), ("hrs", "hrs"), ("kg", "kg")),
    price_range=(12, 850),
    price_step=1,
    iban_spec=("GB", 18),
    terms_native="Payment within {days} days",
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "vat20", "layout": "a", "lang": "native"},
        {"tax": "vat20", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "vat20", "layout": "a", "lang": "native", "many_items": True},
        {"tax": "vat20", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "vat20", "layout": "b", "lang": "native", "cross_border": True,
         "currency": "EUR", "symbol_mode": "code"},
        {"tax": "vat20", "layout": "a", "lang": "native"},
        {"tax": "vat20", "layout": "c", "lang": "native"},
        {"tax": "vat20", "layout": "b", "lang": "native", "ambiguous_date": True},
    ),
)
