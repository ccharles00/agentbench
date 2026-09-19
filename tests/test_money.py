"""Money formatting and canonical amount string tests."""
from decimal import Decimal

import pytest

from categories.invoices.generator import money


class TestMinorStrings:
    def test_zero_minor_units(self):
        assert money.to_minor_string(Decimal("132000"), "JPY") == "132000"

    def test_two_minor_units(self):
        assert money.to_minor_string(Decimal("1234.5"), "USD") == "1234.50"

    def test_rounding_half_up(self):
        assert money.to_minor_string(Decimal("1.005"), "USD") == "1.01"
        assert money.to_minor_string(Decimal("2.675"), "USD") == "2.68"


class TestDisplayStyles:
    def test_western(self):
        assert money.display_amount(Decimal("1234567.89"), "USD") == "1,234,567.89"

    def test_european(self):
        assert money.display_amount(Decimal("1234567.89"), "EUR", "european") == "1.234.567,89"

    def test_indian(self):
        assert money.display_amount(Decimal("1234567.0"), "INR", "indian") == "12,34,567.00"
        assert money.display_amount(Decimal("100000.0"), "INR", "indian") == "1,00,000.00"
        assert money.display_amount(Decimal("1000.0"), "INR", "indian") == "1,000.00"

    def test_space_grouping(self):
        assert money.display_amount(Decimal("1234567.0"), "IDR", "space") == "1 234 567.00"

    def test_zero_minor_no_decimals(self):
        assert money.display_amount(Decimal("132000"), "JPY") == "132,000"

    def test_unknown_style_rejected(self):
        with pytest.raises(ValueError):
            money.display_amount(Decimal("1"), "USD", "roman")


class TestDigits:
    def test_arabic_indic(self):
        assert money.to_arabic_indic("1234.56") == "١٢٣٤.٥٦"


class TestRateFormatting:
    @pytest.mark.parametrize(("value", "expected"), [
        (Decimal("19.00"), "19"),
        (Decimal("7"), "7"),
        (Decimal("1.65"), "1.65"),
        (Decimal("10.0"), "10"),
        (Decimal("8.875"), "8.875"),
    ])
    def test_fmt_rate(self, value, expected):
        assert money.fmt_rate(value) == expected
