"""Scoring pipeline (spec B4.3).

Reads cached raw responses (never re-calls APIs), maps them to canonical
fields via each adapter's to_canonical, compares against ground truth, and
writes results/{dataset_version}/{split}/:

- summary.json       metrics per tool (B4.2) with Wilson 95% CIs and counts
- by_dimension.json  the same metrics broken down by every category dimension
- per_doc.jsonl      one row per (tool, document, variant)
- failures.jsonl     every non-correct comparison, with the rendered string

Unscored (doc, field) pairs (DECISIONS.md #19) are excluded from every
denominator, including document exact-match.
"""
from __future__ import annotations

import importlib
import json
import time
from pathlib import Path

from core.config import ROOT, category_manifest

from .aggregate import dimension_values, score_document
from .metrics import summarize


def _load_field_context(manifest: dict):
    mod_path = manifest.get("comparators_module")
    if not mod_path:
        return None
    return importlib.import_module(mod_path).field_context


def score_split(config: dict, category: str, split: str, tools: str = "all",
                cache_root: Path | None = None,
                results_root: Path | None = None) -> Path:
    from core.harness.cache import Cache
    from core.harness.run import (ALL_VARIANTS, iter_doc_files,
                                  load_adapters, load_ground_truths)

    manifest = category_manifest(category)
    fields = {name: spec["comparator"] for name, spec in manifest["fields"].items()}
    dims = manifest.get("dimensions", [])
    field_context = _load_field_context(manifest)

    adapters = load_adapters(manifest, config)
    if tools != "all":
        wanted = {t.strip() for t in tools.split(",") if t.strip()}
        adapters = {t: a for t, a in adapters.items() if t in wanted}
    if not adapters:
        raise SystemExit("no adapters to score")

    docs = iter_doc_files(manifest, split, list(ALL_VARIANTS))
    truths = load_ground_truths(manifest, split, {d.doc_id for d in docs})

    cache = Cache(cache_root)
    per_doc_lines: list[dict] = []
    failure_lines: list[dict] = []
    summaries: dict[str, dict] = {}
    by_dim: dict[str, dict] = {}

    for tid, adapter in adapters.items():
        version = adapter.version()
        all_rows: list[dict] = []
        doc_rows: list[dict] = []
        # per (doc, variant): dimension coordinates + its rows/doc row
        units: list[tuple[dict, list[dict], dict]] = []

        for doc in docs:
            gt = truths[doc.doc_id]
            rec = cache.get(tid, version, doc.sha256)
            prediction = None
            error = "not_run"
            cost = 0.0
            latency = None
            if rec is not None:
                error = rec.get("error")
                cost = float(rec.get("cost_usd", "0") or 0)
                latency = rec.get("latency_ms")
                if not error:
                    from core.harness.adapter_base import RawResult
                    from decimal import Decimal
                    prediction = adapter.to_canonical(RawResult(
                        payload=rec.get("raw"),
                        latency_ms=float(latency or 0),
                        cost_usd=Decimal(rec.get("cost_usd", "0") or 0),
                    ))

            rows, exact, _failed = score_document(
                gt, prediction, doc.variant, fields, field_context)
            for row in rows:
                row["tool"] = tid
                if row["outcome"] != "correct":
                    failure_lines.append(row)
            all_rows.extend(rows)
            doc_row = {"tool": tid, "doc_id": doc.doc_id, "variant": doc.variant,
                       "exact_match": exact, "error": error, "cost_usd": cost,
                       "latency_ms": latency}
            doc_rows.append(doc_row)
            units.append((dimension_values(gt, doc.variant, dims), rows, doc_row))

        summaries[tid] = {"tool_version": version,
                          "display_name": adapter.display_name,
                          **summarize(all_rows, doc_rows)}

        tool_dims: dict[str, dict] = {}
        for dim in dims:                      # slice one dimension at a time
            groups: dict[str, dict] = {}
            for values, rows, doc_row in units:
                value = values.get(dim)
                if value is None:
                    continue
                g = groups.setdefault(str(value), {"rows": [], "docs": []})
                g["rows"].extend(rows)
                g["docs"].append(doc_row)
            tool_dims[dim] = {v: summarize(g["rows"], g["docs"])
                              for v, g in groups.items()}
        by_dim[tid] = tool_dims
        per_doc_lines.extend(doc_rows)

    results_dir = (results_root or ROOT / "results") / config["dataset_version"] / split
    results_dir.mkdir(parents=True, exist_ok=True)

    header = {"category": category, "dataset_version": config["dataset_version"],
              "split": split, "generated_at": time.strftime("%Y-%m-%d"),
              "methodology": "categories/%s/site_copy.md + DECISIONS.md" % category}

    def _dumpj(name: str, obj: dict) -> None:
        (results_dir / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _dumpj("summary.json", header | {"tools": summaries})
    _dumpj("by_dimension.json", header | {"tools": by_dim})
    with open(results_dir / "per_doc.jsonl", "w", encoding="utf-8") as fh:
        for line in per_doc_lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    with open(results_dir / "failures.jsonl", "w", encoding="utf-8") as fh:
        for line in failure_lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    for tid, s in summaries.items():
        em = s["documents"]
        print(f"[{tid}] exact-match {em['successes']}/{em['count']}"
              f" ({em['rate']:.1%}, Wilson95 {em['wilson95'][0]:.1%}–{em['wilson95'][1]:.1%})"
              f" · field acc {s['field_accuracy']['rate']:.1%}")
    print(f"results -> {results_dir}")
    return results_dir
