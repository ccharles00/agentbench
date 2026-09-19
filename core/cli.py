"""Benchmark CLI — a thin, category-agnostic dispatcher (spec B0, B8).

Category work is delegated to plugin modules declared in
``categories/<category_id>/category.yaml``:

- ``generator_module``  -> ``run(config, split=..., countries=..., limit=...)``
- ``selfcheck_module``  -> ``run(config, split=...)``

Usage:
    python -m core.cli generate --category invoices --split public
    python -m core.cli selfcheck --category invoices --split public
"""
from __future__ import annotations

import argparse
import importlib

import yaml

from core.config import ROOT, load_config

_COMMAND_TO_MODULE_KEY = {
    "generate": "generator_module",
    "selfcheck": "selfcheck_module",
}


def category_manifest(category: str) -> dict:
    path = ROOT / "categories" / category / "category.yaml"
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bench", description="Benchmark pipeline CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--category", default="invoices")
        sp.add_argument("--split", default="public", choices=["public", "private"])

    sp_generate = sub.add_parser("generate", help="generate a dataset split")
    add_common(sp_generate)
    sp_generate.add_argument("--countries", default=None,
                             help="comma-separated country codes (default: all in config)")
    sp_generate.add_argument("--limit", type=int, default=None,
                             help="generate only the first N documents per country")

    sp_check = sub.add_parser("selfcheck", help="validate a generated split (spec B2.8)")
    add_common(sp_check)

    args = parser.parse_args(argv)

    manifest = category_manifest(args.category)
    module_name = manifest[_COMMAND_TO_MODULE_KEY[args.command]]
    module = importlib.import_module(module_name)
    config = load_config()

    if args.command == "generate":
        countries = args.countries.split(",") if args.countries else None
        module.run(config, split=args.split, countries=countries, limit=args.limit)
    else:
        module.run(config, split=args.split)


if __name__ == "__main__":
    main()
