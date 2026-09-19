"""ID generation tests: IBAN mod-97, CLABE, USCC, GSTIN, RFC."""
import importlib
import random

from categories.invoices.generator import ids

# module `in` is a Python keyword — import it by string (as generate.py does)
_in_mod = importlib.import_module("categories.invoices.generator.countries.in")


class TestIban:
    def test_known_valid_iban(self):
        # canonical example from ISO 13616 documentation
        assert ids.iban_is_valid("GB82 WEST 1234 5698 7654 32")

    def test_generated_ibans_valid(self):
        rng = random.Random(42)
        for code, length in (("DE", 18), ("GB", 18), ("SA", 22), ("AE", 19)):
            assert ids.iban_is_valid(ids.make_iban(rng, code, length)), code

    def test_corrupted_iban_detected(self):
        rng = random.Random(1)
        iban = ids.make_iban(rng, "DE", 18)
        bad = iban[:-1] + ("0" if iban[-1] != "0" else "1")
        assert not ids.iban_is_valid(bad)

    def test_display_grouping_round_trip(self):
        rng = random.Random(7)
        iban = ids.make_iban(rng, "SA", 22)
        assert ids.iban_display(iban).replace(" ", "") == iban


class TestClabe:
    def test_length_and_checksum(self):
        rng = random.Random(3)
        clabe = ids.make_clabe(rng)
        assert len(clabe) == 18 and clabe.isdigit()
        assert ids.clabe_check_digit(clabe[:17]) == clabe[17]


class TestUscc:
    def test_generated_codes_valid(self):
        from categories.invoices.generator.countries import cn
        for name in cn.SPEC.vendors:
            display, normalized = cn._structural_uscc(name)
            assert display == normalized
            assert ids.uscc_is_valid(normalized), normalized

    def test_structure(self):
        from categories.invoices.generator.countries import cn
        code = cn._structural_uscc("深圳市华信电子有限公司")[1]
        assert code[0] in "159Y" and code[2:8].isdigit() and len(code) == 18

    def test_stable_per_name(self):
        from categories.invoices.generator.countries import cn
        assert cn._structural_uscc("上海东方贸易有限公司")[1] == \
            cn._structural_uscc("上海东方贸易有限公司")[1]

    def test_corrupted_check_char_detected(self):
        from categories.invoices.generator.countries import cn
        code = cn._structural_uscc("test")[1]
        alphabet = ids.USCC_ALPHABET
        bad = code[:-1] + alphabet[(alphabet.index(code[-1]) + 1) % len(alphabet)]
        assert not ids.uscc_is_valid(bad)

    def test_rejected_old_bad_code(self):
        # the exact malformed code found in the 2026-09-19 data review
        assert not ids.uscc_is_valid("H1QW9U96QL54NB7U8K")


class TestGstin:
    def test_generated_codes_valid(self):
        for name in _in_mod.SPEC.vendors:
            display, normalized = _in_mod._structural_gstin(name)
            assert normalized in display
            assert ids.gstin_is_valid(normalized), normalized

    def test_structure(self):
        code = _in_mod._structural_gstin("Shree Ganesh Traders Pvt. Ltd.")[1]
        assert (len(code) == 15 and code[:2].isdigit() and code[2:7].isalpha()
                and code[7:11].isdigit() and code[13] == "Z")

    def test_stable_per_name(self):
        assert _in_mod._structural_gstin("Mumbai Freight Systems Pvt. Ltd.")[1] == \
            _in_mod._structural_gstin("Mumbai Freight Systems Pvt. Ltd.")[1]


class TestRfc:
    def test_generated_codes_valid(self):
        from categories.invoices.generator.countries import mx
        for name in mx.SPEC.vendors:            # personas morales -> 12 chars
            code = mx._rfc_for(name, fisica=False)
            assert len(code) == 12 and ids.rfc_is_valid(code), code
        for name in mx.SPEC.vendors_fisica:     # personas físicas -> 13 chars
            code = mx._rfc_for(name, fisica=True)
            assert len(code) == 13 and ids.rfc_is_valid(code), code

    def test_rejected_old_bad_code(self):
        # month 76 is impossible — the kind of RFC the old generator made
        assert not ids.rfc_is_valid("VWH527641YL2")

    def test_stable_per_name(self):
        from categories.invoices.generator.countries import mx
        assert mx._rfc_for("Distribuidora del Norte S.A. de C.V.") == \
            mx._rfc_for("Distribuidora del Norte S.A. de C.V.")
