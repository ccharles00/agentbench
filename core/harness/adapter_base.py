"""Adapter interface and shared result types (spec B3.1).

Adapters map vendor output to our canonical field names WITHOUT fixing values:
no correcting dates, number formats, or currencies on the vendor's behalf.
Only unit/label mapping is allowed. Anything the vendor didn't return is null
(absent from the canonical dict).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class DocFile:
    """One file a tool will actually see (one degradation variant, one page set)."""
    doc_id: str
    variant: str          # clean_pdf | scan | bad_scan | phone_photo
    path: Path | None     # None for synthetic/in-memory tasks (test stubs)
    sha256: str

    @classmethod
    def from_path(cls, doc_id: str, variant: str, path: Path) -> "DocFile":
        return cls(doc_id, variant, path, sha256_file(path))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RawResult:
    payload: object                     # opaque vendor response
    latency_ms: float = 0.0
    cost_usd: Decimal = Decimal("0")
    error: str | None = None            # non-None = this call failed
    transient: bool = False             # True = retryable
    meta: dict | None = None            # document context (e.g. doc_id) for
                                        # canonicalization; never answers


class TransientError(Exception):
    """Retryable vendor failure (rate limit, 5xx, timeout)."""


@runtime_checkable
class ExtractorAdapter(Protocol):
    tool_id: str
    display_name: str

    def version(self) -> str: ...
    def estimate_cost(self, doc: DocFile) -> Decimal: ...
    def extract(self, doc: DocFile) -> RawResult: ...
    def to_canonical(self, raw: RawResult) -> dict: ...
