"""The _example stub category through the full pipeline (spec B0).

Runs the real harness (cache, cost gate, retries) and the real scorer over
three fake tasks with a fake adapter — proving the core is category-agnostic
and the metric arithmetic is right, with zero files and zero spend.
"""
import json

import pytest

from core.config import load_config
from core.harness.run import run as harness_run
from core.scoring.pipeline import score_split


@pytest.fixture()
def example_run(tmp_path):
    config = load_config()
    summary = harness_run(config, "_example", "public", confirm=True,
                          cache_root=tmp_path / "cache")
    results_dir = score_split(config, "_example", "public",
                              cache_root=tmp_path / "cache",
                              results_root=tmp_path / "results")
    return summary, results_dir


def test_harness_ran_all_docs(example_run):
    summary, _ = example_run
    assert summary["fake_extractor"]["documents"] == 3
    assert summary["fake_extractor"]["failed"] == 0
    assert summary["fake_extractor"]["cached"] == 0


def test_results_files_exist(example_run):
    _, results_dir = example_run
    for name in ("summary.json", "by_dimension.json", "per_doc.jsonl",
                 "failures.jsonl"):
        assert (results_dir / name).exists()


def test_metric_arithmetic(example_run):
    _, results_dir = example_run
    s = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    tool = s["tools"]["fake_extractor"]

    # doc 1 exact; doc 2 wrong count; doc 3 hallucinated count
    em = tool["documents"]
    assert (em["successes"], em["count"]) == (1, 3)
    assert em["rate"] == pytest.approx(1 / 3, abs=1e-3)

    fa = tool["field_accuracy"]
    assert (fa["successes"], fa["count"]) == (4, 6)     # 3 IDs + 1 count correct

    h = tool["hallucination_rate"]
    assert (h["successes"], h["count"]) == (1, 6)

    assert tool["api_failure_rate"]["count"] == 3
    assert tool["api_failure_rate"]["successes"] == 0
    assert tool["cost_per_correct_doc_usd"] == 0.0


def test_by_dimension(example_run):
    _, results_dir = example_run
    bd = json.loads((results_dir / "by_dimension.json").read_text(encoding="utf-8"))
    sizes = bd["tools"]["fake_extractor"]["size"]
    assert sizes["small"]["documents"]["count"] == 2
    assert sizes["small"]["documents"]["successes"] == 1     # EX-0001 only
    assert sizes["large"]["documents"]["count"] == 1
    assert sizes["large"]["documents"]["successes"] == 0
    variants = bd["tools"]["fake_extractor"]["variant"]
    assert variants["clean_pdf"]["documents"]["count"] == 3


def test_failures_file_lists_non_correct(example_run):
    _, results_dir = example_run
    lines = [json.loads(l) for l in
             (results_dir / "failures.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    by_doc = {l["doc_id"]: l for l in lines}
    assert by_doc["EX-0002"]["outcome"] == "incorrect"
    assert by_doc["EX-0003"]["outcome"] == "hallucination"
    assert by_doc["EX-0003"]["field"] == "count"


def test_second_run_is_fully_cached(example_run, tmp_path):
    _, _ = example_run
    config = load_config()
    summary = harness_run(config, "_example", "public", confirm=True,
                          cache_root=tmp_path / "cache")
    assert summary["fake_extractor"]["cached"] == 3
