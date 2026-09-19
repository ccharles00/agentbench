"""Cost control (spec B3.4, C3.2).

Prints the estimated total per tool and overall before a run; requires
--confirm; hard-stops at BUDGET_USD from config. The owner approves spend —
the harness enforces it.
"""
from __future__ import annotations

from decimal import Decimal


class BudgetExceeded(SystemExit):
    pass


def format_usd(v: Decimal) -> str:
    return f"${v:.4f}"


def check_plan(estimates: dict[str, Decimal], budget_usd: Decimal,
               confirm: bool) -> None:
    """estimates: tool_id -> estimated total. Refuses unconfirmed or over-budget runs."""
    total = sum(estimates.values(), Decimal("0"))
    print("Estimated cost per tool:")
    for tool, est in sorted(estimates.items()):
        print(f"  {tool:32s} {format_usd(est)}")
    print(f"  {'TOTAL':32s} {format_usd(total)}   (budget {format_usd(budget_usd)})")
    if total > budget_usd:
        raise BudgetExceeded(
            f"estimate {format_usd(total)} exceeds BUDGET_USD {format_usd(budget_usd)} — "
            "raise the budget in config.yaml or narrow --tools/--variants")
    if not confirm:
        print("Dry run — nothing was called. Re-run with --confirm to execute.")
        raise SystemExit(0)
    print("Confirmed — executing.")
