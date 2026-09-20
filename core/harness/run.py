"""Harness runner (spec B3.4).

- Cost estimate per tool printed before any call; --confirm required; hard
  stop at BUDGET_USD.
- Raw responses cached under cache/{tool}/{version}/{sha}.json; cached docs
  are skipped, so rescoring never re-calls APIs.
- Exponential backoff on TransientError; permanent failures are recorded and
  count against the tool.
- Wall-clock latency recorded per call.
"""
from __future__ import annotations

import importlib
import json
import time
from decimal import Decimal
from pathlib import Path

from core.config import category_manifest, data_dir

from .adapter_base import DocFile, RawResult, TransientError, sha256_file
from .cache import Cache

RETRY_ATTEMPTS = 3          # beyond the first call
BACKOFF_BASE_S = 0.5
# HTTP-level transients (429 quota, 5xx capacity) need real waits; only
# network blips get the fast exponential path.
LONG_BACKOFF_S = (15, 30, 60)

ALL_VARIANTS = ("clean_pdf", "scan", "bad_scan", "phone_photo")


def load_adapters(manifest: dict, config: dict) -> dict[str, object]:
    reg_path = manifest.get("adapter_registry")
    if not reg_path:
        return {}
    registry = importlib.import_module(reg_path).REGISTRY
    enabled = set(config.get("tools") or registry.keys())   # empty = all
    return {tid: cls(config=config) for tid, cls in sorted(registry.items())
            if tid in enabled}


def iter_doc_files(manifest: dict, split: str,
                   variants: list[str]) -> list[DocFile]:
    source = manifest.get("task_source", {"kind": "manifest"})
    if source.get("kind") == "module":
        module = importlib.import_module(source["module"])
        docs = module.tasks()
        return [d for d in docs if d.variant in variants]

    base = data_dir(split)
    with open(base / "manifest.json", "r", encoding="utf-8") as fh:
        m = json.load(fh)
    docs: list[DocFile] = []
    for entry in m["documents"]:
        for variant, files in entry["variants"].items():
            if variant not in variants:
                continue
            for rel in files:
                docs.append(DocFile.from_path(entry["doc_id"], variant, base / rel))
    return docs


def load_ground_truths(manifest: dict, split: str, doc_ids: set[str]) -> dict[str, dict]:
    """Ground truth for a split, from the manifest files or a module task source."""
    source = manifest.get("task_source", {"kind": "manifest"})
    if source.get("kind") == "module":
        module = importlib.import_module(source["module"])
        return {doc_id: module.ground_truth(doc_id) for doc_id in sorted(doc_ids)}
    gt_dir = data_dir(split) / "ground_truth"
    out = {}
    for doc_id in sorted(doc_ids):
        with open(gt_dir / f"{doc_id}.json", "r", encoding="utf-8") as fh:
            out[doc_id] = json.load(fh)
    return out


def _record(adapter, doc: DocFile, raw: RawResult) -> dict:
    return {
        "tool_id": adapter.tool_id,
        "tool_version": adapter.version(),
        "doc_id": doc.doc_id,
        "variant": doc.variant,
        "sha256": doc.sha256,
        "raw": raw.payload,
        "latency_ms": round(raw.latency_ms, 1),
        "cost_usd": str(raw.cost_usd),
        "error": raw.error,
    }


def call_with_retries(adapter, doc: DocFile) -> dict:
    delay = BACKOFF_BASE_S
    for attempt in range(RETRY_ATTEMPTS + 1):
        t0 = time.perf_counter()
        try:
            raw = adapter.extract(doc)
        except TransientError as exc:
            if attempt == RETRY_ATTEMPTS:
                return _record(adapter, doc, RawResult(
                    payload={"exception": str(exc)}, error=str(exc), transient=True))
            msg = str(exc)
            wait = LONG_BACKOFF_S[min(attempt, len(LONG_BACKOFF_S) - 1)] \
                if ("HTTP 429" in msg or "HTTP 5" in msg) else delay
            print(f"    transient ({str(exc)[:120]}); retrying in {wait}s", flush=True)
            time.sleep(wait)
            delay *= 2
            continue
        except Exception as exc:                      # permanent failure
            return _record(adapter, doc, RawResult(
                payload={"exception": str(exc)}, error=str(exc)))
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if not raw.latency_ms:
            raw.latency_ms = elapsed_ms
        return _record(adapter, doc, raw)
    raise AssertionError("unreachable")


def run(config: dict, category: str, split: str, tools: str = "all",
        variants: str = "all", confirm: bool = False, limit: int | None = None,
        cache_root: Path | None = None) -> dict:
    from . import cost as cost_mod

    manifest = category_manifest(category)
    adapters = load_adapters(manifest, config)
    if tools != "all":
        wanted = {t.strip() for t in tools.split(",") if t.strip()}
        unknown = wanted - set(adapters)
        if unknown:
            raise SystemExit(f"unknown tools {sorted(unknown)}; "
                             f"known: {sorted(adapters)}")
        adapters = {t: a for t, a in adapters.items() if t in wanted}
    if not adapters:
        raise SystemExit("no adapters registered for this category")

    variant_list = list(ALL_VARIANTS) if variants == "all" else \
        [v.strip() for v in variants.split(",") if v.strip()]
    docs = iter_doc_files(manifest, split, variant_list)
    if limit is not None:
        docs = docs[:limit]
    if not docs:
        raise SystemExit(f"no documents found for split {split!r}")

    estimates = {tid: sum((a.estimate_cost(d) for d in docs), Decimal("0"))
                 for tid, a in adapters.items()}
    cost_mod.check_plan(estimates, Decimal(str(config.get("budget_usd", 0))),
                        confirm=confirm)

    cache = Cache(cache_root)
    summary = {}
    for tid, adapter in adapters.items():
        version = adapter.version()
        cached = failed = 0
        print(f"[{tid} v{version}] {len(docs)} documents", flush=True)
        for doc in docs:
            rec = cache.get(tid, version, doc.sha256)
            if rec is not None and rec.get("error") is None:
                cached += 1
                continue
            record = call_with_retries(adapter, doc)
            if record["error"]:
                failed += 1
            cache.put(tid, version, doc.sha256, record)
            print(f"  {doc.doc_id} [{doc.variant}] "
                  f"{'ERROR: ' + record['error'][:100] if record['error'] else 'ok'}",
                  flush=True)
        summary[tid] = {"tool_version": version, "documents": len(docs),
                        "cached": cached, "failed": failed}
        print(f"  cached: {cached}, new: {len(docs) - cached}, failed: {failed}",
              flush=True)
    return summary
