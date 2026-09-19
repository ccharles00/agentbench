"""Three fake tasks for the _example stub category (spec B0).

No files, no network: documents are identified by doc_id alone, so the
pipeline test exercises the harness and scorer without touching disk data.
"""
from __future__ import annotations

import hashlib

from core.harness.adapter_base import DocFile

_TRUTH = {
    "EX-0001": {"fields": {"widget_id": "WDG-001", "count": "3"},
                "dimensions": {"size": "small"}, "rendered_strings": {}},
    "EX-0002": {"fields": {"widget_id": "WDG-002", "count": "7"},
                "dimensions": {"size": "large"}, "rendered_strings": {}},
    "EX-0003": {"fields": {"widget_id": "WDG-003", "count": None},
                "dimensions": {"size": "small"}, "rendered_strings": {}},
}


def ground_truth(doc_id: str) -> dict:
    gt = dict(_TRUTH[doc_id])
    gt["doc_id"] = doc_id
    gt.setdefault("unscored_fields", [])
    return gt


def tasks() -> list[DocFile]:
    return [
        DocFile(doc_id=doc_id, variant="clean_pdf", path=None,
                sha256=hashlib.sha256(doc_id.encode()).hexdigest())
        for doc_id in sorted(_TRUTH)
    ]
