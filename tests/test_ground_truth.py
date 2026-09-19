"""Ground-truth schema and money-math invariants, checked without rendering."""
import json
import random

from core.config import load_config
from categories.invoices.generator import selfcheck
from categories.invoices.generator.build import build_invoice
from categories.invoices.generator.countries import us as us_mod
from categories.invoices.generator.model import dump_ground_truth

CONFIG = load_config()


def _build(country_code: str, doc_index: int):
    spec = us_mod.SPEC if country_code == "US" else None
    assert spec is not None
    spec.tax_scenarios = us_mod.make_scenarios(CONFIG["tax_rates"]["US"])
    doc_id = f"{country_code}-{doc_index:04d}"
    seed = int.from_bytes(random.Random(doc_id).randbytes(8), "big")
    return build_invoice(spec, random.Random(seed), doc_id, spec.doc_plan[doc_index - 1])


class TestGroundTruth:
    def test_schema_and_invariants(self):
        inv = _build("US", 1)
        gt = inv.to_ground_truth()
        selfcheck.check_gt_schema(gt)
        problems = selfcheck.Problems()
        selfcheck.check_amounts(gt, inv.doc_id, problems)
        selfcheck.check_identity(gt, inv.doc_id, problems)
        selfcheck.check_dates(gt, inv.doc_id, problems)
        selfcheck.check_tax_rates(gt, inv.doc_id, CONFIG["tax_rates"], problems)
        selfcheck.check_payment_account(gt, inv.doc_id, problems)
        assert problems.ok(), problems.items

    def test_many_items_doc(self):
        inv = _build("US", 6)
        assert inv.dimensions["template"] == "us_a"
        assert 18 <= len(inv.items) <= 25
        problems = selfcheck.Problems()
        selfcheck.check_identity(inv.to_ground_truth(), inv.doc_id, problems)
        assert problems.ok(), problems.items

    def test_deterministic_build(self):
        gt1 = dump_ground_truth(_build("US", 2).to_ground_truth())
        gt2 = dump_ground_truth(_build("US", 2).to_ground_truth())
        assert gt1 == gt2

    def test_serialization_is_stable_json(self):
        gt = _build("US", 1).to_ground_truth()
        assert json.loads(dump_ground_truth(gt)) == gt
