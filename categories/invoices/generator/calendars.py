"""Calendar conversions (spec B2.2, B2.5).

Ground truth dates are always ISO 8601 Gregorian. Documents render them in
native calendars and formats — Japanese era years and Thai Buddhist years are
the interesting failures (2569 taken literally, Reiwa math gone wrong).
Every conversion here round-trips, and the self-check (B2.8) enforces that.
"""
from __future__ import annotations

from datetime import date

# Japanese eras: (start date, kanji, romaji). Era year 1 is a partial Gregorian year.
_JAPANESE_ERAS = [
    (date(2019, 5, 1), "令和", "Reiwa"),
    (date(1989, 1, 8), "平成", "Heisei"),
    (date(1926, 12, 25), "昭和", "Showa"),
    (date(1912, 7, 30), "大正", "Taisho"),
    (date(1868, 9, 8), "明治", "Meiji"),
]

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]
THAI_MONTHS_ABBR = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]


def to_japanese_era(d: date) -> tuple[str, int]:
    for start, kanji, _romaji in _JAPANESE_ERAS:
        if d >= start:
            return kanji, d.year - start.year + 1
    raise ValueError(f"date {d} precedes the Meiji era")


def from_japanese_era(era_kanji: str, era_year: int, month: int, day: int) -> date:
    for start, kanji, _romaji in _JAPANESE_ERAS:
        if kanji == era_kanji:
            if era_year < 1:
                raise ValueError("era year must be >= 1")
            d = date(start.year + era_year - 1, month, day)
            if d < start:
                raise ValueError(
                    f"{era_kanji} year {era_year}, {month:02d}-{day:02d} predates era start {start}")
            return d
    raise ValueError(f"unknown Japanese era: {era_kanji!r}")


def format_japanese_date(d: date) -> str:
    kanji, year = to_japanese_era(d)
    return f"{kanji}{year}年{d.month}月{d.day}日"


def to_buddhist_year(d: date) -> int:
    return d.year + 543


def from_buddhist_year(buddhist_year: int, month: int, day: int) -> date:
    return date(buddhist_year - 543, month, day)  # date() validates


def format_thai_date(d: date, abbr: bool = False) -> str:
    months = THAI_MONTHS_ABBR if abbr else THAI_MONTHS
    return f"{d.day} {months[d.month - 1]} {to_buddhist_year(d)}"


def round_trip(d: date, calendar: str) -> date:
    """Convert out to the native calendar and back; must be lossless (B2.8)."""
    if calendar == "gregorian":
        return date(d.year, d.month, d.day)
    if calendar == "japanese_era":
        kanji, year = to_japanese_era(d)
        return from_japanese_era(kanji, year, d.month, d.day)
    if calendar == "buddhist":
        return from_buddhist_year(to_buddhist_year(d), d.month, d.day)
    raise ValueError(f"unknown calendar: {calendar!r}")
