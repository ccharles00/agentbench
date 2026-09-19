"""Common normalizers and comparators (spec B4.1).

Normalization is applied identically to ground truth and predictions.

Strictness is deliberate and is part of the benchmark's contract:
- Amounts must arrive as plain decimal values at the currency's precision
  (as the shared prompt demands). "1.234" for one thousand two hundred
  thirty-four is wrong; "1234.5" for USD 1234.50 is right (trailing zeros
  are formatting, not value).
- Dates must be ISO 8601 Gregorian. Swapped day/month is wrong.
- IDs: spaces/hyphens removed, uppercased — nothing else.

Null handling (B4.1): truth null + pred null = correct; truth null +
pred non-null = hallucination; truth non-null + pred null = miss.
Unscored (doc, field) pairs are excluded upstream, not here.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

_WS = re.compile(r"\s+")


def norm_text(s: str) -> str:
    """NFKC, casefold, trim, collapse whitespace, strip trailing punctuation."""
    s = unicodedata.normalize("NFKC", str(s)).casefold()
    s = _WS.sub(" ", s).strip()
    return s.rstrip(".,;:")


def norm_identifier(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    s = "".join(ch for ch in s if not ch.isspace() and ch != "-")
    return s.upper()


_AMOUNT_RE = re.compile(r"^[+-]?(\d+)(\.\d+)?$")


def parse_amount(value) -> Decimal | None:
    """Plain decimal only. No thousands separators, no comma decimals."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # floats arrive from vendor JSON; go through repr to avoid binary noise
        value = repr(value)
    if not isinstance(value, str):
        return None
    s = value.strip().replace("\u00a0", "").replace(" ", "")
    if not _AMOUNT_RE.match(s):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_date(value) -> date | None:
    """ISO 8601 (YYYY-MM-DD), optionally with a time suffix."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$", s)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def _quantize(d: Decimal, minor_units: int) -> Decimal:
    return d.quantize(Decimal(1).scaleb(-minor_units))


def _outcome(truth, pred) -> str | None:
    """Null-pattern classification; None means 'compare the values'."""
    if truth is None and pred is None:
        return "correct"
    if truth is None and pred is not None:
        return "hallucination"
    if truth is not None and pred is None:
        return "incorrect"          # miss
    return None


def exact_comparator(truth, pred, ctx: dict) -> str:
    if (o := _outcome(truth, pred)) is not None:
        return o
    return "correct" if norm_text(truth) == norm_text(pred) else "incorrect"


def name_comparator(truth, pred, ctx: dict) -> str:
    """Accept the printed name or any stored alternate (B4.1)."""
    if (o := _outcome(truth, pred)) is not None:
        return o
    n = norm_text(pred)
    if n == norm_text(truth):
        return "correct"
    for alt in ctx.get("alternates", []):
        if alt and n == norm_text(alt):
            return "correct"
    return "incorrect"


def identifier_comparator(truth, pred, ctx: dict) -> str:
    if (o := _outcome(truth, pred)) is not None:
        return o
    return ("correct" if norm_identifier(truth) == norm_identifier(pred)
            else "incorrect")


def date_comparator(truth, pred, ctx: dict) -> str:
    if (o := _outcome(truth, pred)) is not None:
        return o
    t, p = parse_date(truth), parse_date(pred)
    if t is None or p is None:
        return "incorrect"
    return "correct" if t == p else "incorrect"


def amount_comparator(truth, pred, ctx: dict) -> str:
    """Exact equality at the currency's minor-unit precision.

    ctx["minor_units"] (from the category's comparators module) selects the
    precision; default 2.
    """
    if (o := _outcome(truth, pred)) is not None:
        return o
    minor = ctx.get("minor_units", 2)
    t, p = parse_amount(truth), parse_amount(pred)
    if t is None or p is None:
        return "incorrect"
    return "correct" if _quantize(t, minor) == _quantize(p, minor) else "incorrect"


def rate_set_comparator(truth, pred, ctx: dict) -> str:
    """Set comparison of numeric rates (duplicates collapse)."""
    if truth is None and pred is None:
        return "correct"
    if truth is None or pred is None:
        return "hallucination" if truth is None else "incorrect"
    def _rates(v) -> set | None:
        if not isinstance(v, (list, tuple)):
            return None
        out = set()
        for r in v:
            d = parse_amount(r)
            if d is None:
                return None
            out.add(d.normalize())
        return out
    t, p = _rates(truth), _rates(pred)
    if t is None or p is None:
        return "incorrect"
    return "correct" if t == p else "incorrect"


def integer_comparator(truth, pred, ctx: dict) -> str:
    if (o := _outcome(truth, pred)) is not None:
        return o
    try:
        return "correct" if int(str(truth).strip()) == int(str(pred).strip()) \
            else "incorrect"
    except (TypeError, ValueError):
        return "incorrect"
