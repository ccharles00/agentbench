"""ID generation tests: IBAN mod-97 and CLABE checksums."""
import random

from categories.invoices.generator import ids


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
