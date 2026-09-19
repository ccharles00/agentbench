"""Tax IDs, bank accounts, and invoice-number primitives.

Ground truth normalizes IDs by removing spaces/hyphens and uppercasing (spec
B4.1); generators here produce realistic *display* forms plus the normalized
form. IBANs get real mod-97 check digits so the self-check can validate them.

Structural identifiers (CN USCC, IN GSTIN, MX RFC) implement their published
check-character rules so extractors that validate IDs never reject a correct
read (DECISIONS.md #20). Where a vendor name must always map to the same ID
(stable identity pairs), generators derive from `stable_rng(name)`.

GSTIN's checksum uses the widely implemented mod-36 alternating-weight scheme;
USCC uses the GB 32100-2015 mod-31 scheme with weights 3^i mod 31.
"""
from __future__ import annotations

import hashlib
import random
from string import ascii_uppercase, digits

D10 = "0123456789"


def random_digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(D10) for _ in range(n))


def random_alnum(rng: random.Random, n: int) -> str:
    pool = digits + ascii_uppercase
    return "".join(rng.choice(pool) for _ in range(n))


def stable_rng(label: str) -> random.Random:
    """Deterministic RNG from a label (e.g. a vendor name).

    Same label -> same ID on every document: a company never appears with two
    different tax IDs (DECISIONS.md #20).
    """
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _char_value(c: str) -> str:
    return str(int(c, 36)) if c.isalpha() else c


def iban_make(country_code: str, bban: str) -> str:
    """Build a valid IBAN with real mod-97 check digits (ISO 13616)."""
    rearranged = bban + country_code.upper() + "00"
    num = int("".join(_char_value(c) for c in rearranged))
    check = 98 - (num % 97)
    return f"{country_code.upper()}{check:02d}{bban}"


def iban_is_valid(iban: str) -> bool:
    s = iban.replace(" ", "").upper()
    if len(s) < 15 or not s.isalnum():
        return False
    num = "".join(_char_value(c) for c in s[4:] + s[:4])
    return int(num) % 97 == 1


def iban_display(iban: str) -> str:
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))


def make_iban(rng: random.Random, country_code: str, bban_len: int) -> str:
    return iban_make(country_code, random_alnum(rng, bban_len) if country_code in {"GB"}
                     else random_digits(rng, bban_len))


# --- CLABE (Mexico): 3 bank + 3 city + 12 account + check digit ---------------

_CLABE_BANKS = ["002", "012", "021", "036", "044", "072", "127", "137", "400"]


def clabe_check_digit(clabe17: str) -> str:
    weights = (3, 7, 1)
    total = sum(int(d) * weights[i % 3] for i, d in enumerate(clabe17))
    return str((10 - total % 10) % 10)


def make_clabe(rng: random.Random) -> str:
    # 3 bank + 3 city + 11 account + 1 check digit = 18 digits
    body = rng.choice(_CLABE_BANKS) + random_digits(rng, 3) + random_digits(rng, 11)
    return body + clabe_check_digit(body)


# --- CN unified social credit code (GB 32100-2015) ----------------------------
# 18 chars: type + category + 6-digit division code + 9-char org code + check.
# Alphabet is 31 characters (no I, O, S, V, Z); check is mod-31, weights 3^i.

USCC_ALPHABET = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)


def uscc_check_char(body17: str) -> str:
    total = sum(USCC_ALPHABET.index(c) * w for c, w in zip(body17, _USCC_WEIGHTS))
    return USCC_ALPHABET[(31 - total % 31) % 31]


def uscc_is_valid(code: str) -> bool:
    if len(code) != 18 or any(c not in USCC_ALPHABET for c in code):
        return False
    if code[0] not in "159Y" or not code[2:8].isdigit():
        return False
    return uscc_check_char(code[:17]) == code[17]


# --- IN GSTIN -----------------------------------------------------------------
# 15 chars: 2-digit state code + 10-char PAN + entity digit + 'Z' + check char.
# Check uses the widely implemented mod-36 alternating 1/2 weight scheme.

_B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_check_char(body14: str) -> str:
    total = 0
    for i, c in enumerate(body14):
        p = _B36.index(c) * (i % 2 + 1)
        total += p - 35 if p >= 36 else p
    return _B36[(36 - total % 36) % 36]


def gstin_is_valid(code: str) -> bool:
    if len(code) != 15 or any(c not in _B36 for c in code):
        return False
    if not (code[:2].isdigit() and code[2:7].isalpha() and code[7:11].isdigit()
            and code[11].isalpha() and code[12].isdigit() and code[13] == "Z"):
        return False
    return gstin_check_char(code[:14]) == code[14]


# --- MX RFC -------------------------------------------------------------------
# 12 chars (persona moral): 3 letters + YYMMDD + 3-char homoclave.
# 13 chars (persona física): 4 letters + YYMMDD + homoclave. The date must be
# valid; the homoclave is SAT-assigned (no public check algorithm).

def rfc_is_valid(code: str) -> bool:
    from datetime import date as _date
    if len(code) not in (12, 13) or not code.isalnum() or not code.isupper():
        return False
    n = len(code)
    if not code[: n - 9].isalpha() or not code[n - 9:n - 3].isdigit():
        return False
    yy, mm, dd = int(code[n - 9:n - 7]), int(code[n - 7:n - 5]), int(code[n - 5:n - 3])
    year = 2000 + yy if yy <= 26 else 1900 + yy
    try:
        _date(year, mm, dd)
    except ValueError:
        return False
    return True
