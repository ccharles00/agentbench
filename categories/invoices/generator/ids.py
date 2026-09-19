"""Tax IDs, bank accounts, and invoice-number primitives.

Ground truth normalizes IDs by removing spaces/hyphens and uppercasing (spec
B4.1); generators here produce realistic *display* forms plus the normalized
form. IBANs get real mod-97 check digits so the self-check can validate them.
"""
from __future__ import annotations

import random
from string import ascii_uppercase, digits

D10 = "0123456789"


def random_digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(D10) for _ in range(n))


def random_alnum(rng: random.Random, n: int) -> str:
    pool = digits + ascii_uppercase
    return "".join(rng.choice(pool) for _ in range(n))


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
