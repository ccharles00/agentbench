"""MCP server tools over the static JSON API (spec B7) — scaffold.

Pure functions reading the built API directory (run `make build-api` first).
The stdio JSON-RPC transport wiring lands with the M3 build; these functions
are the tested core and become MCP tools 1:1. They never claim certainty
beyond the data: every ranking carries counts and Wilson intervals.
"""
from __future__ import annotations

import json
from pathlib import Path


class Api:
    def __init__(self, site_dir: Path):
        self.root = Path(site_dir) / "api" / "v1"
        self._cache: dict[str, dict] = {}

    def get(self, rel: str) -> dict:
        if rel not in self._cache:
            self._cache[rel] = json.loads(
                (self.root / rel).read_text(encoding="utf-8"))
        return self._cache[rel]


def list_categories(api: Api) -> list[dict]:
    return api.get("index.json")["categories"]


def list_tools(api: Api, category: str = "invoices") -> dict:
    idx = api.get(f"categories/{category}/index.json")
    board = api.get(f"categories/{category}/leaderboard.json")
    return {"tools": [
        {"tool_id": t["tool_id"], "display_name": t["display_name"],
         "tool_version": t["tool_version"],
         "test_date": board["test_date"]}
        for t in board["tools"]], "dataset_version": idx["dataset_versions"][0]}


def get_leaderboard(api: Api, split: str = "public", dimension: str | None = None,
                    value: str | None = None, category: str = "invoices") -> dict:
    if dimension and value:
        return api.get(f"categories/{category}/dimensions/{dimension}/{value}.json")
    name = "leaderboard.json" if split == "public" else "leaderboard_private.json"
    return api.get(f"categories/{category}/{name}")


def recommend_extractor(api: Api, countries: list[str] | None = None,
                        degradation: str | None = None,
                        max_cost_per_doc_usd: float | None = None,
                        min_exact_match: float | None = None,
                        split: str = "public", category: str = "invoices") -> dict:
    board = get_leaderboard(api, split=split, category=category)
    candidates = []
    for t in board["tools"]:
        detail = None
        if countries:
            cc = countries[0].upper()
            try:
                detail = api.get(f"categories/{category}/dimensions/country/{cc}.json")
                t = dict(t, document_exact_match=detail["tools"][t["tool_id"]]
                         ["documents"])
            except FileNotFoundError:
                continue
        if min_exact_match is not None and t["document_exact_match"]["rate"] < min_exact_match:
            continue
        if (max_cost_per_doc_usd is not None
                and t["mean_cost_per_doc_usd"] > max_cost_per_doc_usd):
            continue
        candidates.append(t)
    candidates.sort(key=lambda t: (-t["document_exact_match"]["rate"],
                                   t["cost_per_correct_doc_usd"] or 9e9))
    top = candidates[0] if candidates else None
    rationale = None
    if top:
        em = top["document_exact_match"]
        scope = f" for {countries[0].upper()}" if countries else ""
        rationale = (f"{top['display_name']} ranks first{scope} with "
                     f"{em['rate']:.1%} document exact-match "
                     f"(n={em['count']}, Wilson95 {em['wilson95'][0]:.0%}–"
                     f"{em['wilson95'][1]:.0%}) at "
                     f"${top['cost_per_correct_doc_usd']:.4f} per correct document.")
    return {"recommendation": top, "ranked": candidates,
            "rationale": rationale,
            "methodology": board["methodology"],
            "split": split, "sample_size_caveat":
            "Rates carry 95% Wilson intervals; check n before acting."}


def get_failures(api: Api, results_root: Path, tool_id: str,
                 country: str | None = None, field: str | None = None,
                 limit: int = 5, split: str = "public") -> list[dict]:
    board = get_leaderboard(api, split=split)
    path = results_root / board["dataset_version"] / split / "failures.jsonl"
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("tool") != tool_id:
            continue
        if country and not row["doc_id"].startswith(country.upper()):
            continue
        if field and row.get("field") != field:
            continue
        out.append(row)
        if len(out) >= limit:
            break
    return out
