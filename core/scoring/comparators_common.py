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
    """Strip pure formatting: whitespace, hyphens, dots, slashes; uppercase.

    Spec B4.1 names spaces and hyphens; dots and slashes are added because
    CNPJ (33.637.151/0001-04), NPWP, and GSTIN display formats are pure
    punctuation (DECISIONS.md #21). Applied identically to truth and
    prediction, so formatted and bare forms match either way.
    """
    s = unicodedata.normalize("NFKC", str(s))
    s = "".join(ch for ch in s if ch not in " \t-./")
    return s.upper()


_AMOUNT_RE = re.compile(r"^[+-]?(\d+)(\.\d+)?$")

# Display clutter a vendor may attach to an amount; stripped before parsing,
# symmetrically for truth and predictions (DECISIONS.md #22).
_CURRENCY_SYMBOLS = "$€£¥₹฿₩₺₫"
_CURRENCY_PREFIXES = ("R$", "Rp", "Rs", "NT$", "CA$", "A$", "MX$", "US$",
                      "د.إ", "ر.س")

# Unambiguous grouped forms (both separators present = self-describing):
#   1,234,567.89 -> US style   |   1.234.567,89 -> EU style
_US_STYLE = re.compile(r"^(\d{1,3}(?:,\d{3})+)\.(\d+)$")
_EU_STYLE = re.compile(r"^(\d{1,3}(?:\.\d{3})+),(\d+)$")


def _strip_currency(s: str) -> str:
    for prefix in _CURRENCY_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):].lstrip()
            break
    s = s.strip(_CURRENCY_SYMBOLS).strip()
    s = re.sub(r"\s?[A-Za-z]{3}$", "", s)          # trailing ISO code
    s = re.sub(r"^[A-Za-z]{3}\s?", "", s)          # leading ISO code
    return s


def parse_amount(value) -> Decimal | None:
    """Value-exact amount parsing (spec B4.1, DECISIONS.md #22).

    Plain decimals always parse. Display formatting is tolerated ONLY when
    unambiguous: currency symbols around the number, and grouped forms that
    contain both separators (self-describing US or EU style). "1.234" for
    1234, or "1,234" with no other separator, stays unparseable — there is
    no way to know which convention was meant.
    """
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
    s = _strip_currency(value.replace("\u00a0", "").replace(" ", ""))
    if _AMOUNT_RE.match(s):
        return Decimal(s)
    if (m := _US_STYLE.match(s)):
        return Decimal(m[1].replace(",", "") + "." + m[2])
    if (m := _EU_STYLE.match(s)):
        return Decimal(m[1].replace(".", "") + "." + m[2])
    if re.fullmatch(r"-?\d+,\d{2}", s):
        return Decimal(s.replace(",", "."))        # "548,01" EU decimal comma
    return None


def parse_date(value) -> date | None:
    """ISO 8601 always; other layouts only when they are unambiguous.

    Spec B4.1: dates must equal the ISO Gregorian date; swapped day/month is
    wrong. Numeric M/D/YYYY (or D/M/YYYY) is accepted only when one part
    exceeds 12 (or they are equal), since only then does the layout reveal
    itself (DECISIONS.md #22). English month names are unambiguous in any
    arrangement. Everything else stays unparseable.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$", s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", s)
    if m:
        a, b, y = int(m[1]), int(m[2]), int(m[3])
        if a == b:                                  # same date either way
            try:
                return date(y, a, a)
            except ValueError:
                return None
        if a > 12 or b > 12:                        # layout reveals itself
            day, month = (a, b) if a > 12 else (b, a)
            try:
                return date(y, month, day)
            except ValueError:
                return None
        return None
    m = re.match(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$", s) \
        or re.match(r"^(\d{1,2})\.?\s+([A-Za-z]{3,9}),?\s+(\d{4})$", s)
    if m:
        first, second, year = m[1], m[2], m[3]
        month_str = first if not first.isdigit() else second
        day_str = second if not first.isdigit() else first
        mo = _MONTHS.get(month_str.casefold()[:3])
        if mo:
            try:
                return date(int(year), mo, int(day_str))
            except ValueError:
                return None
    return None


_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


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
