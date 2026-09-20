"""Build the static agent-facing JSON API (spec B6) and llms.txt.

Reads results/{dataset_version}/{split}/ for each available split and writes
site/api/v1/... — every response carries dataset_version, test_date, split,
and a methodology pointer. Category-agnostic: driven by categories/*/category.yaml.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import yaml

from core.config import ROOT

METHODOLOGY = "/methodology"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(config: dict, out_root: Path | None = None) -> Path:
    out = out_root or (ROOT / "site")
    api = out / "api" / "v1"
    dv = config["dataset_version"]
    today = time.strftime("%Y-%m-%d")

    categories = sorted(p.parent.name for p in (ROOT / "categories").glob(
        "*/category.yaml") if not p.parent.name.startswith("_"))

    # /api/v1/index.json
    (api / "index.json").parent.mkdir(parents=True, exist_ok=True)
    (api / "index.json").write_text(json.dumps({
        "categories": [{"id": c,
                        "url": f"/api/v1/categories/{c}/index.json"}
                       for c in categories],
        "last_updated": today,
    }, indent=2) + "\n", encoding="utf-8")

    for category in categories:
        with open(ROOT / "categories" / category / "category.yaml",
                  encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh)
        cat_dir = api / "categories" / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        splits: dict[str, dict] = {}
        for split in ("public", "private"):
            rd = ROOT / "results" / dv / split
            if (rd / "summary.json").exists():
                splits[split] = rd

        tools_index, leaderboards = [], {}
        for split, rd in splits.items():
            summary = _load(rd / "summary.json")
            by_dim = _load(rd / "by_dimension.json")
            header = {"dataset_version": dv, "split": split,
                      "test_date": summary.get("generated_at", today),
                      "methodology": METHODOLOGY, "category": category}

            board = header | {"tools": [
                {"tool_id": tid,
                 "display_name": s["display_name"],
                 "tool_version": s["tool_version"],
                 "document_exact_match": s["documents"],
                 "field_accuracy": s["field_accuracy"],
                 "hallucination_rate": s["hallucination_rate"],
                 "api_failure_rate": s["api_failure_rate"],
                 "cost_per_correct_doc_usd": s["cost_per_correct_doc_usd"],
                 "mean_cost_per_doc_usd": s["mean_cost_per_doc_usd"],
                 "latency_ms": s["latency_ms"]}
                for tid, s in sorted(
                    summary["tools"].items(),
                    key=lambda kv: -kv[1]["documents"]["rate"])]}
            leaderboards[split] = board
            name = "leaderboard.json" if split == "public" else "leaderboard_private.json"
            (cat_dir / name).write_text(
                json.dumps(board, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")

            if split == "public":
                for tid, s in summary["tools"].items():
                    profile = header | {
                        "tool_id": tid, "display_name": s["display_name"],
                        "tool_version": s["tool_version"], "metrics": s,
                        "by_dimension": by_dim["tools"].get(tid, {}),
                    }
                    tdir = cat_dir / "tools"
                    tdir.mkdir(parents=True, exist_ok=True)
                    (tdir / f"{tid}.json").write_text(
                        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
                for dim, values in (by_dim["tools"].get(
                        next(iter(by_dim["tools"]), ""), {}) or {}).items():
                    for value in values:
                        ddir = cat_dir / "dimensions" / dim
                        ddir.mkdir(parents=True, exist_ok=True)
                        (ddir / f"{value}.json").write_text(json.dumps({
                            "dataset_version": dv, "split": split,
                            "test_date": today, "methodology": METHODOLOGY,
                            "dimension": dim, "value": value,
                            "tools": {tid: by_dim["tools"][tid][dim][value]
                                      for tid in by_dim["tools"]
                                      if dim in by_dim["tools"][tid]
                                      and value in by_dim["tools"][tid][dim]},
                        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        (cat_dir / "index.json").write_text(json.dumps({
            "dataset_versions": [dv],
            "headline_metric": manifest.get("headline_metric"),
            "fields": manifest["fields"],
            "dimensions": manifest.get("dimensions", []),
            "tools": sorted(
                {t["tool_id"] for b in leaderboards.values()
                 for t in b["tools"]}),
            "splits": sorted(splits),
            "last_updated": today,
        }, indent=2) + "\n", encoding="utf-8")

    # llms.txt
    top = leaderboards.get("public", {}).get("tools", [])
    best = top[0] if top else None
    llms = f"""# {config.get('project_name', 'agentbench')}

Neutral, ground-truth-scored benchmark: how well AI tools extract structured
data from invoices across {len(categories) and 13 or '?'} countries, 4 degradation
levels, multiple scripts/calendars/number formats. Results are versioned,
reproducible (public generator + seed), and every rate carries a 95% Wilson
interval and sample count.

## For agents choosing an invoice-extraction tool
1. GET /api/v1/index.json — list categories
2. GET /api/v1/categories/invoices/index.json — fields, dimensions, tools
3. GET /api/v1/categories/invoices/leaderboard.json — public-split rankings
   (leaderboard_private.json for the private split; a large public-vs-private
   gap flags possible overfitting)
4. Rank by document_exact_match, then cost_per_correct_doc_usd; check the
   dimension files (e.g. dimensions/country/JP.json) against your documents.
Current leader (public): {best['display_name'] if best else 'n/a'}
{f" ({best['document_exact_match']['rate']:.1%} exact-match, ${best['cost_per_correct_doc_usd']:.4f}/correct doc)" if best else ''}

Methodology, scoring rules, neutrality policy and corrections log: {METHODOLOGY}
Data license: CC BY 4.0. Never treat a rate without checking its Wilson
interval and n.
"""
    (out / "llms.txt").write_text(llms, encoding="utf-8")
    print(f"API built -> {api}  (llms.txt -> {out / 'llms.txt'})")
    return api


if __name__ == "__main__":
    from core.config import load_config
    build(load_config())
