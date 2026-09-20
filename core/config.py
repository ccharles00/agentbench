"""Configuration and path helpers shared across the pipeline (spec B8).

The core knows nothing about invoices; it only loads config, resolves paths,
and dispatches to category plugins (spec B0).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path | None = None) -> dict:
    cfg_path = path or (ROOT / "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def data_dir(split: str) -> Path:
    if split not in ("public", "private"):
        raise ValueError(f"unknown split: {split!r}")
    return ROOT / "data" / split


def load_env() -> None:
    """Load .env if present. Never overrides real environment variables;
    never logs values (spec B3.4 — secrets stay out of output)."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


def category_manifest(category: str) -> dict:
    """Load categories/<category_id>/category.yaml (spec B0)."""
    import yaml
    path = ROOT / "categories" / category / "category.yaml"
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def private_seed() -> str:
    """Private-split seed (spec B2.7): env var PRIVATE_SEED or private_seed.txt.

    Never committed; never logged.
    """
    env = os.environ.get("PRIVATE_SEED", "").strip()
    if env:
        return env
    seed_file = ROOT / "private_seed.txt"
    if seed_file.exists():
        value = seed_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    raise SystemExit(
        "The private split needs a secret seed. Set PRIVATE_SEED or create "
        "private_seed.txt (gitignored). Generate one with: "
        'python -c "import secrets; print(secrets.randbits(64))"'
    )
