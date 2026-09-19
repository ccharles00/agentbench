"""Generator entry point (spec B2).

Deterministic from the split seed: the RNG for each document is derived as
SHA256(split:seed:doc_id), so the same seed regenerates byte-identical ground
truth and visually identical documents (B2.1).
"""
from __future__ import annotations

import hashlib
import importlib
import json
import random
import shutil
import tempfile
from pathlib import Path

from core.config import ROOT, data_dir

from . import contact_sheets, degrade, render
from .build import build_invoice
from .model import dump_ground_truth

GENERATOR_VERSION = "2026.1.0"

COUNTRY_MODULES = {
    cc: f"categories.invoices.generator.countries.{cc.lower()}"
    for cc in ("US", "GB", "DE", "IN", "CN", "JP", "KR", "BR", "MX", "SA", "AE", "ID", "TH")
}


def _doc_seed(seed: str, doc_id: str) -> int:
    digest = hashlib.sha256(f"{seed}:{doc_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _load_spec(country: str, tax_table: dict):
    module = importlib.import_module(COUNTRY_MODULES[country])
    spec = module.SPEC
    spec.tax_scenarios = module.make_scenarios(tax_table[country])
    return module, spec


def run(config: dict, split: str = "public", countries: list[str] | None = None,
        limit: int | None = None) -> None:
    seed = str(config["public_seed"]) if split == "public" else None
    if seed is None:
        from core.config import private_seed
        seed = private_seed()

    wanted = countries or config["countries"]
    unknown = [c for c in wanted if c not in COUNTRY_MODULES]
    if unknown:
        raise SystemExit(f"unknown countries: {unknown}; known: {sorted(COUNTRY_MODULES)}")

    docs_per_country = int(config["docs_per_country"])
    tax_table = config["tax_rates"]
    base = data_dir(split)
    gt_dir = base / "ground_truth"
    docs_dir = base / "documents"
    gt_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    renderer = render.PdfRenderer()
    try:
        for country in wanted:
            module, spec = _load_spec(country, tax_table)
            n = len(spec.doc_plan) if limit is None else min(limit, len(spec.doc_plan))
            if n != docs_per_country and limit is None:
                raise SystemExit(
                    f"{country}: doc_plan has {len(spec.doc_plan)} entries, "
                    f"config says {docs_per_country}")
            print(f"[{country}] generating {n} invoices ...", flush=True)
            for i in range(1, n + 1):
                doc_id = f"{country}-{i:04d}"
                plan = spec.doc_plan[i - 1]
                inv = build_invoice(spec, random.Random(_doc_seed(seed, doc_id)),
                                    doc_id, plan)

                doc_dir = docs_dir / doc_id
                if doc_dir.exists():
                    shutil.rmtree(doc_dir)          # keep regeneration idempotent
                doc_dir.mkdir(parents=True)

                gt_path = gt_dir / f"{doc_id}.json"
                gt_path.write_text(dump_ground_truth(inv.to_ground_truth()), encoding="utf-8")

                with tempfile.TemporaryDirectory() as tmp:
                    html_path = Path(tmp) / f"{doc_id}.html"
                    html_path.write_text(render.build_html(inv), encoding="utf-8")
                    pdf_path = doc_dir / "clean.pdf"
                    renderer.render(html_path, pdf_path, inv.page_size)

                variants = degrade.make_variants(pdf_path, doc_dir, doc_id,
                                                 _doc_seed(seed, doc_id + ":degrade"))
                files = {"clean_pdf": [f"documents/{doc_id}/clean.pdf"]}
                for vf in variants:
                    files.setdefault(vf.variant, []).append(
                        f"documents/{doc_id}/{vf.path.name}")
                all_files = [f for v in files.values() for f in v]
                entries.append({
                    "doc_id": doc_id,
                    "country": country,
                    "ground_truth": f"ground_truth/{doc_id}.json",
                    "variants": files,
                    "multipage": any("_p2." in f for f in all_files),
                })
                print(f"  {doc_id}: {inv.total_display} · {inv.template_id}", flush=True)
    finally:
        renderer.close()

    entries.sort(key=lambda e: e["doc_id"])
    manifest = {
        "category": "invoices",
        "dataset_version": config["dataset_version"],
        "split": split,
        "seed": seed,
        "generator_version": GENERATOR_VERSION,
        "documents": entries,
    }
    (base / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    contact_sheets.make_all(base)
    print(f"Done: {len(entries)} invoices -> {base}", flush=True)


if __name__ == "__main__":
    from core.config import load_config
    run(load_config())
