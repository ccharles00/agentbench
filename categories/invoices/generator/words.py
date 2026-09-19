"""Amount-in-words, used for realistic display only — never scored.

Indian invoices print "Rupees ... Only"; Chinese fapiao print the uppercase
amount (大写金额). Both are classic extraction hazards and good realism.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _two(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")


def english_words(n: int) -> str:
    """Indian-system English words: crore / lakh / thousand / hundred."""
    if n < 0:
        raise ValueError("negative amounts not supported")
    if n < 100:
        return _two(n)
    for value, name in ((10 ** 7, "crore"), (10 ** 5, "lakh"), (1000, "thousand"),
                        (100, "hundred")):
        if n >= value:
            q, rest = divmod(n, value)
            head = english_words(q) if value >= 1000 else _two(q)
            out = f"{head} {name}"
            if rest:
                out += f" {english_words(rest)}"
            return out
    raise AssertionError("unreachable")


def rupees_in_words(amount: Decimal) -> str:
    """'Rupees One Lakh Twenty Thousand Only' (whole rupees; common on Indian invoices)."""
    n = int(abs(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"Rupees {_two(0) if n == 0 else english_words(n).title()} Only"


_CN_DIGITS = "零壹贰叁肆伍陆柒捌玖"
_CN_U4 = ["", "拾", "佰", "仟"]
_CN_BIG = ["", "万", "亿"]


def _cn_four(n: int) -> str:
    parts: list[str] = []
    zero_pending = False
    for i in (3, 2, 1, 0):
        d = (n // 10 ** i) % 10
        if d:
            if zero_pending and parts:
                parts.append("零")
            parts.append(_CN_DIGITS[d] + _CN_U4[i])
            zero_pending = False
        elif parts:
            zero_pending = True
    return "".join(parts)


def _cn_int(n: int) -> str:
    groups: list[int] = []
    while n:
        groups.append(n % 10000)
        n //= 10000
    out: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        s = _cn_four(g)
        if i == 0 and len(groups) > 1 and g < 1000:
            s = "零" + s
        out.append(s + _CN_BIG[i])
    return "".join(out)


def chinese_upper_amount(value: Decimal) -> str:
    """RMB uppercase: 1320.00 -> '壹仟叁佰贰拾元整' (spec: fapiao style, simplified)."""
    q = abs(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    yuan = int(q)
    cents = int(q * 100) - yuan * 100
    jiao, fen = divmod(cents, 10)
    if yuan == 0 and jiao == 0 and fen == 0:
        return "零元整"
    out = ""
    if yuan > 0:
        out += _cn_int(yuan) + "元"
    elif jiao or fen:
        out += "零"
    if jiao:
        out += _CN_DIGITS[jiao] + "角"
    if fen:
        out += _CN_DIGITS[fen] + "分"
    if not jiao and not fen:
        out += "整"
    return out
