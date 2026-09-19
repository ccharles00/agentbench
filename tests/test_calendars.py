"""Calendar conversion tests — credibility lives here (spec C3.6)."""
from datetime import date

import pytest

from categories.invoices.generator import calendars as cal


class TestJapaneseEra:
    def test_reiwa_year(self):
        assert cal.to_japanese_era(date(2026, 3, 4)) == ("令和", 8)

    def test_era_boundary(self):
        # Heisei ended 2019-04-30; Reiwa began 2019-05-01
        assert cal.to_japanese_era(date(2019, 4, 30)) == ("平成", 31)
        assert cal.to_japanese_era(date(2019, 5, 1)) == ("令和", 1)

    def test_format(self):
        assert cal.format_japanese_date(date(2026, 3, 4)) == "令和8年3月4日"

    def test_round_trip_reiwa(self):
        assert cal.from_japanese_era("令和", 8, 3, 4) == date(2026, 3, 4)

    def test_era_year_one_before_start_rejected(self):
        # 令和 1年 started 2019-05-01; March of that year is still Heisei 31
        with pytest.raises(ValueError):
            cal.from_japanese_era("令和", 1, 3, 4)

    def test_unknown_era_rejected(self):
        with pytest.raises(ValueError):
            cal.from_japanese_era("神武", 1, 1, 1)

    @pytest.mark.parametrize("d", [
        date(2019, 5, 1), date(2019, 12, 31), date(2020, 2, 29),
        date(2025, 7, 15), date(2026, 9, 19),
    ])
    def test_round_trip(self, d):
        assert cal.round_trip(d, "japanese_era") == d


class TestBuddhist:
    def test_year_offset(self):
        assert cal.to_buddhist_year(date(2026, 3, 4)) == 2569

    def test_format(self):
        assert cal.format_thai_date(date(2026, 3, 4)) == "4 มีนาคม 2569"
        assert cal.format_thai_date(date(2026, 3, 4), abbr=True) == "4 มี.ค. 2569"

    def test_round_trip(self):
        assert cal.from_buddhist_year(2569, 3, 4) == date(2026, 3, 4)
        assert cal.round_trip(date(2025, 12, 31), "buddhist") == date(2025, 12, 31)

    def test_invalid_date_rejected(self):
        with pytest.raises(ValueError):
            cal.from_buddhist_year(2569, 2, 30)


class TestGregorian:
    def test_round_trip(self):
        d = date(2025, 11, 23)
        assert cal.round_trip(d, "gregorian") == d

    def test_unknown_calendar(self):
        with pytest.raises(ValueError):
            cal.round_trip(date(2025, 1, 1), "persian")
