"""Currency amounts and display formatting (spec B2.5, B2.2).

Ground truth stores amounts as decimal strings with exactly the currency's
minor-unit precision (JPY 0 places, USD 2, KWD 3). Everything here is Decimal;
floats are never used for money.

Display formatting is a separate, purely visual concern: western grouping
(1,234.56), European (1.234,56), Indian lakh/crore (1,23,456.00), and space
grouping, plus Arabic-Indic digit rendering. A vendor misreading 1.234,56 is
exactly the kind of failure this benchmark exists to catch.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MINOR_UNITS = {
    "USD": 2, "EUR": 2, "GBP": 2, "INR": 2, "CNY": 2, "JPY": 0,
    "KRW": 0, "BRL": 2, "MXN": 2, "SAR": 2, "AED": 2, "IDR": 2, "THB": 2,
}

# Where the currency symbol sits when rendering: prefix (¥132,000) or suffix
# (1.234,56 €). SAR/AED use Arabic-script abbreviations, suffixed.
SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "CNY": "¥",
    "JPY": "¥", "KRW": "₩", "BRL": "R$", "MXN": "$", "SAR": "ر.س",
    "AED": "د.إ", "IDR": "Rp", "THB": "฿",
}
SYMBOL_AFTER = {"EUR", "SAR", "AED"}

ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def minor_units(currency: str) -> int:
    return MINOR_UNITS[currency]


def quantize(value: Decimal, currency: str) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-MINOR_UNITS[currency]),
                          rounding=ROUND_HALF_UP)


def to_minor_string(value: Decimal, currency: str) -> str:
    """Canonical ground-truth form: '132000' (JPY), '1234.56' (USD), '12.345' (KWD)."""
    return f"{quantize(value, currency):f}"


def fmt_rate(rate: Decimal) -> str:
    """Rate as printed in ground truth: '19', '7', '1.65' — no trailing zeros."""
    s = format(rate.normalize(), "f")
    return s


def _split(int_part: str, sep: str) -> str:
    out: list[str] = []
    while len(int_part) > 3:
        out.insert(0, int_part[-3:])
        int_part = int_part[:-3]
    out.insert(0, int_part)
    return sep.join(out)


def group_indian(int_part: str) -> str:
    """1,00,000-style grouping (lakh/crore)."""
    if len(int_part) <= 3:
        return int_part
    head, tail = int_part[:-3], int_part[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join([*parts, tail])


def display_amount(value: Decimal, currency: str, style: str = "western") -> str:
    """Render a value in a given national convention, without currency marks.

    styles: 'western' 1,234.56 | 'european' 1.234,56 |
            'indian' 1,23,456.78 | 'space' 1 234 567.89
    """
    q = quantize(value, currency)
    sign = "-" if q < 0 else ""
    s = f"{abs(q):f}"
    int_part, _, frac = s.partition(".")
    if style == "western":
        grouped, dec = _split(int_part, ","), "."
    elif style == "european":
        grouped, dec = _split(int_part, "."), ","
    elif style == "indian":
        grouped, dec = group_indian(int_part), "."
    elif style == "space":
        grouped, dec = _split(int_part, " "), "."
    else:
        raise ValueError(f"unknown number style: {style!r}")
    out = sign + grouped
    if MINOR_UNITS[currency] > 0:
        out += dec + frac
    return out


def to_arabic_indic(s: str) -> str:
    return s.translate(ARABIC_INDIC)
