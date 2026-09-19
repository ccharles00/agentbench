"""US invoices: MM/DD dates, state sales tax, routing + account numbers.

Bank details are display-only; ground truth `payment_account` is null here
because the schema only normalizes IBAN/CLABE (spec B2.5) — see DECISIONS.md.
"""
from __future__ import annotations

import random
from datetime import date

from .. import ids
from ..build import CountrySpec


def _tax_id(rng: random.Random) -> tuple[str, str]:
    ein = f"{rng.randrange(10, 99)}-{ids.random_digits(rng, 7)}"
    return ein, ein.replace("-", "")


def _invoice_no(rng: random.Random, d: date) -> str:
    style = rng.randrange(3)
    if style == 0:
        return f"INV-{d.year}-{rng.randrange(1, 10000):04d}"
    if style == 1:
        return f"#{rng.randrange(1000, 10000)}"
    return f"SI-{d.year}{d.month:02d}-{rng.randrange(1, 1000):03d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.month:02d}/{d.day:02d}/{d.year}"


def _bank_lines(rng: random.Random) -> list[str]:
    return [f"Routing No. {ids.random_digits(rng, 9)}  ·  Account No. {ids.random_digits(rng, 10)}"]


def make_scenarios(cfg: dict) -> dict:
    # cfg: state -> rate, from config.yaml `tax_rates.US` (owner verifies)
    rates = [__import__("decimal").Decimal(str(r)) for r in cfg.values()]
    return {"sales_tax": {"mode": "exclusive", "rates": rates, "pick_one": True}}


SPEC = CountrySpec(
    code="US", name="United States", currency="USD",
    native_lang="en", scripts=("Latn",), font_stack=("Noto Sans",),
    page_size="Letter",
    tax_label="Sales Tax",
    vendors=(
        "Cascade Office Supply LLC", "Redwood Analytics Inc.", "Great Plains Logistics Co.",
        "Summit Components Corp.", "Lakeside Catering Services", "Blue Ridge Software LLC",
        "Harbor Freight Forwarding Inc.", "Sierra Design Group",
    ),
    customers=(
        "Meridian Trading LLC", "Oakfield Manufacturing Inc.", "Pinewood Consulting Group",
        "Silverline Media Corp.", "Copperfield Industries LLC", "Northgate Retail Partners",
    ),
    vendor_addresses=(
        ("1200 Pine Street, Suite 400", "Seattle, WA 98101"),
        ("350 Fifth Avenue", "New York, NY 10118"),
        ("77 Commerce Drive", "Chicago, IL 60601"),
        ("900 Market Street", "San Francisco, CA 94102"),
        ("4100 W Northwest Hwy", "Dallas, TX 75220"),
        ("250 Social Hall Ave", "Salt Lake City, UT 84111"),
    ),
    customer_addresses=(
        ("88 Kearny Street", "San Jose, CA 95113"),
        ("200 Public Square", "Columbus, OH 43215"),
        ("1 Innovation Way", "Austin, TX 78701"),
        ("501 Boylston Street", "Boston, MA 02116"),
    ),
    customer_tax_label="EIN",
    descriptions=(
        "Office chair, ergonomic mesh, adjustable arms",
        "Monthly retainer — analytics dashboard maintenance and support",
        "Freight — Seattle to Denver, 2 pallets, liftgate delivery",
        "Cloud hosting — compute and storage, monthly",
        "Consulting hours — ERP migration, senior consultant",
        "Printer toner, black, high-yield (pack of 4)",
        "Warehouse storage — Q3, climate-controlled",
        "Translation services — EN to ES, 24 pages, certified",
        "Safety gloves, cut-resistant, size L (12 pairs)",
        "Custom rack enclosure, 42U, with cable management and thermal kit",
        "Catering — board meeting, 12 people, full service",
        "Software license — annual subscription, 25 seats",
    ),
    units=(("pcs", "pcs"), ("ea", "ea"), ("hrs", "hrs"), ("mo", "mo"), ("lbs", "lbs")),
    price_range=(15, 900),
    price_step=1,
    big_price_range=(400, 4000),
    labels={"tax_id_label": "EIN"},
    terms_native="Net {days} days",
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    bank_lines_gen=_bank_lines,
    doc_plan=(
        {"tax": "sales_tax", "layout": "a", "lang": "native"},
        {"tax": "sales_tax", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "sales_tax", "layout": "a", "lang": "native"},
        {"tax": "sales_tax", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "sales_tax", "layout": "b", "lang": "native"},
        {"tax": "sales_tax", "layout": "a", "lang": "native", "many_items": True},
        {"tax": "sales_tax", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "sales_tax", "layout": "b", "lang": "native", "symbol_mode": "both"},
    ),
)
