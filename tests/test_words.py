"""Amount-in-words tests (display only, but realism matters)."""
from decimal import Decimal

from categories.invoices.generator import words


class TestRupees:
    def test_lakh(self):
        assert words.rupees_in_words(Decimal("120000")) == \
            "Rupees One Lakh Twenty Thousand Only"

    def test_crore(self):
        assert words.rupees_in_words(Decimal("21500000")) == \
            "Rupees Two Crore Fifteen Lakh Only"

    def test_small(self):
        assert words.rupees_in_words(Decimal("450")) == "Rupees Four Hundred Fifty Only"


class TestChineseUpper:
    def test_basic(self):
        assert words.chinese_upper_amount(Decimal("1320.00")) == "壹仟叁佰贰拾元整"

    def test_lakh_sized(self):
        assert words.chinese_upper_amount(Decimal("100500.00")) == "壹拾万零伍佰元整"
        assert words.chinese_upper_amount(Decimal("10000500.00")) == "壹仟万零伍佰元整"

    def test_cents(self):
        assert words.chinese_upper_amount(Decimal("1.20")) == "壹元贰角"
        assert words.chinese_upper_amount(Decimal("0.05")) == "零伍分"
        assert words.chinese_upper_amount(Decimal("12.34")) == "壹拾贰元叁角肆分"

    def test_zero(self):
        assert words.chinese_upper_amount(Decimal("0.00")) == "零元整"


class TestEnglishWords:
    def test_thousands(self):
        assert words.english_words(1234) == "one thousand two hundred thirty-four"
