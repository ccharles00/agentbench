"""Invoice-specific scoring context (spec B0, B4.1).

The core comparators are generic; this module injects the category's
knowledge: amounts compare at the currency's minor-unit precision (JPY 0,
USD 2, KWD 3), read from the ground truth's ISO currency code.
"""
from __future__ import annotations

from categories.invoices.generator import money


def field_context(gt: dict) -> dict:
    currency = (gt.get("fields") or {}).get("currency")
    return {"minor_units": money.MINOR_UNITS.get(currency, 2)}
