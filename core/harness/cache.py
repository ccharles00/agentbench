"""Raw-response cache (spec B3.4).

cache/{tool_id}/{tool_version}/{doc_sha256}.json — one file per (tool,
version, document file). Rescoring never re-calls APIs: the scorer reads
these files.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.config import ROOT


class Cache:
    def __init__(self, root: Path | None = None):
        self.root = root or (ROOT / "cache")

    def path(self, tool_id: str, tool_version: str, sha256: str) -> Path:
        safe_version = tool_version.replace("/", "_").replace(":", "_")
        return self.root / tool_id / safe_version / f"{sha256}.json"

    def get(self, tool_id: str, tool_version: str, sha256: str) -> dict | None:
        p = self.path(tool_id, tool_version, sha256)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def put(self, tool_id: str, tool_version: str, sha256: str,
            record: dict) -> Path:
        p = self.path(tool_id, tool_version, sha256)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return p
