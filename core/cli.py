"""Benchmark CLI — a thin, category-agnostic dispatcher (spec B0, B8).

Category work is delegated to plugin modules declared in
``categories/<category_id>/category.yaml``:

- ``generator_module``  -> ``run(config, split=..., countries=..., limit=...)``
- ``selfcheck_module``  -> ``run(config, split=...)``
- ``task_source``/``adapter_registry``/``comparators_module`` -> harness + scorer

Usage:
    python -m core.cli generate --category invoices --split public
    python -m core.cli selfcheck --category invoices --split public
    python -m core.cli run --category invoices --split public --dry-run
    python -m core.cli score --category invoices --split public
"""
from __future__ import annotations

import argparse
import importlib

from core.config import category_manifest, load_config, load_env

_COMMAND_TO_MODULE_KEY = {
    "generate": "generator_module",
    "selfcheck": "selfcheck_module",
}


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

    sp_run = sub.add_parser("run", help="run tools over a split (spec B3.4)")
    add_common(sp_run)
    sp_run.add_argument("--tools", default="all")
    sp_run.add_argument("--variants", default="all")
    sp_run.add_argument("--limit", type=int, default=None)
    sp_run.add_argument("--dry-run", action="store_true",
                        help="print the cost estimate and exit (no API calls)")
    sp_run.add_argument("--confirm", action="store_true",
                        help="required to actually call paid APIs")

    sp_score = sub.add_parser("score", help="score cached results (spec B4.3)")
    add_common(sp_score)
    sp_score.add_argument("--tools", default="all")

    args = parser.parse_args(argv)

    load_env()
    config = load_config()

    if args.command in _COMMAND_TO_MODULE_KEY:
        manifest = category_manifest(args.category)
        module = importlib.import_module(
            manifest[_COMMAND_TO_MODULE_KEY[args.command]])
        if args.command == "generate":
            countries = args.countries.split(",") if args.countries else None
            module.run(config, split=args.split, countries=countries, limit=args.limit)
        else:
            module.run(config, split=args.split)
    elif args.command == "run":
        from core.harness.run import run as harness_run
        harness_run(config, args.category, args.split, tools=args.tools,
                    variants=args.variants,
                    confirm=args.confirm and not args.dry_run, limit=args.limit)
    else:
        from core.scoring.pipeline import score_split
        score_split(config, args.category, args.split, tools=args.tools)


if __name__ == "__main__":
    main()
