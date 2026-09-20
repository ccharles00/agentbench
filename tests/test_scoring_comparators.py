"""Normalization and comparator edge cases (spec C3.6, B4.1).

These are where credibility lives: lakh grouping, comma decimals,
three-decimal currencies, era/Buddhist dates, null handling, unscored pairs.
"""
from datetime import date

import pytest

from core.scoring.comparators_common import (
    amount_comparator,
    date_comparator,
    exact_comparator,
    identifier_comparator,
    integer_comparator,
    name_comparator,
    norm_identifier,
    norm_text,
    parse_amount,
    parse_date,
    rate_set_comparator,
)


class TestAmounts:
    def test_lakh_grouping_prediction_is_wrong(self):
        # truth 100000.00; "1,00,000.00" is not a plain decimal
        assert parse_amount("1,00,000.00") is None
        assert amount_comparator("100000.00", "100000", {"minor_units": 2}) == "correct"
        assert amount_comparator("100000.00", "1,00,000.00", {"minor_units": 2}) == "incorrect"

    def test_misread_lakh_magnitude(self):
        assert amount_comparator("100000.00", "1000000", {"minor_units": 2}) == "incorrect"

    def test_comma_decimal_prediction_is_wrong(self):
        # German vendor string, unnormalized: must not silently parse
        assert parse_amount("68.396,85") is None
        assert amount_comparator("68396.85", "68396.85", {"minor_units": 2}) == "correct"
        assert amount_comparator("68396.85", "68.396,85", {"minor_units": 2}) == "incorrect"

    def test_german_misread_thousands_as_decimals(self):
        # reading 1.234 as 1.234 instead of 1234 (spec A3)
        assert amount_comparator("1234.00", "1.234", {"minor_units": 2}) == "incorrect"

    def test_three_decimal_currency(self):
        assert amount_comparator("12.345", "12.345", {"minor_units": 3}) == "correct"
        assert amount_comparator("12.345", "12.35", {"minor_units": 3}) == "incorrect"
        assert amount_comparator("12.345", "12.3450", {"minor_units": 3}) == "correct"

    def test_zero_decimal_currency(self):
        assert amount_comparator("132000", "132000", {"minor_units": 0}) == "correct"
        assert amount_comparator("132000", "1320.00", {"minor_units": 0}) == "incorrect"

    def test_trailing_zeros_are_formatting(self):
        assert amount_comparator("1234.50", "1234.5", {"minor_units": 2}) == "correct"
        assert amount_comparator("1234.50", 1234.5, {"minor_units": 2}) == "correct"
        assert amount_comparator("1234.50", 1234, {"minor_units": 2}) == "incorrect"

    def test_negative_prediction(self):
        assert amount_comparator("100.00", "-100.00", {"minor_units": 2}) == "incorrect"


class TestDates:
    def test_iso_required(self):
        assert parse_date("2026-03-04") == date(2026, 3, 4)
        assert parse_date("2026-03-04T00:00:00Z") == date(2026, 3, 4)
        assert parse_date("04/03/2026") is None
        assert parse_date("4 March 2026") is None

    def test_era_date_converted_correctly(self):
        # a tool that converts 令和8年3月4日 properly
        assert date_comparator("2026-03-04", "2026-03-04", {}) == "correct"

    def test_era_date_taken_literally(self):
        # Reiwa 8 read as year 8, or Buddhist 2569 read as 2569
        assert date_comparator("2026-03-04", "0008-03-04", {}) == "incorrect"
        assert date_comparator("2026-03-04", "2569-03-04", {}) == "incorrect"

    def test_swapped_day_month(self):
        assert date_comparator("2026-03-04", "2026-04-03", {}) == "incorrect"

    def test_non_iso_prediction(self):
        assert date_comparator("2026-03-04", "04/03/2026", {}) == "incorrect"


class TestNulls:
    def test_null_null_correct(self):
        for comp in (exact_comparator, date_comparator, amount_comparator,
                     identifier_comparator):
            assert comp(None, None, {}) == "correct"

    def test_hallucination(self):
        assert exact_comparator(None, "something", {}) == "hallucination"
        assert amount_comparator(None, "10.00", {"minor_units": 2}) == "hallucination"

    def test_miss(self):
        assert exact_comparator("truth", None, {}) == "incorrect"
        assert date_comparator("2026-03-04", None, {}) == "incorrect"


class TestIdentifiers:
    def test_spacing_and_hyphens(self):
        assert identifier_comparator("DE123456789", "de 123 456-789", {}) == "correct"
        assert norm_identifier("GB82-WEST-1234") == "GB82WEST1234"

    def test_dots_and_slashes_are_formatting(self):
        # CNPJ and NPWP print formats (DECISIONS.md #21)
        assert identifier_comparator("33637151000104", "33.637.151/0001-04", {}) == "correct"
        assert identifier_comparator("476569725415617", "47.656.972.5415-617", {}) == "correct"
        assert norm_identifier("33.637.151/0001-04") == "33637151000104"

    def test_wrong_value(self):
        assert identifier_comparator("T1234567890123", "T1234567890124", {}) == "incorrect"


class TestNames:
    def test_alternates_accepted(self):
        ctx = {"alternates": ["Tokyo Office Supply K.K."]}
        assert name_comparator("東京オフィスサプライ株式会社",
                               "tokyo office supply k.k.", ctx) == "correct"

    def test_wrong_name(self):
        assert name_comparator("Acme Ltd", "Acme GmbH", {}) == "incorrect"

    def test_normalization(self):
        assert norm_text("  Foo   Bar Ltd. ") == "foo bar ltd"


class TestRateSets:
    def test_duplicates_collapse(self):
        # Indian CGST+SGST prints two 9% lines; a tool returning one "9" is right
        assert rate_set_comparator(["9", "9"], [9], {}) == "correct"

    def test_withholding_excluded_from_truth(self):
        assert rate_set_comparator(["16"], ["16", "10"], {}) == "incorrect"

    def test_order_insensitive(self):
        assert rate_set_comparator(["18", "1.65"], ["1.65", "18"], {}) == "correct"


class TestInteger:
    def test_count(self):
        assert integer_comparator("6", 6, {}) == "correct"
        assert integer_comparator("6", "7", {}) == "incorrect"


class TestUnscoredExclusion:
    def test_unscored_fields_remove_denominators(self):
        # integration of DECISIONS.md #19 at the score_document level
        from core.scoring.aggregate import score_document
        gt = {
            "doc_id": "X", "fields": {"vendor_name": "Acme",
                                      "payment_account": None},
            "unscored_fields": ["payment_account"],
            "rendered_strings": {},
        }
        fields = {"vendor_name": "name", "payment_account": "identifier"}
        rows, exact, _ = score_document(gt, {"vendor_name": "Acme",
                                             "payment_account": "123456789"},
                                        "clean_pdf", fields, None)
        assert exact is True                      # hallucination not counted
        assert [r["field"] for r in rows] == ["vendor_name"]
