"""Comparator registry (spec B0, B4).

The core owns a registry of field comparators; categories declare comparator
*names* per field in their category.yaml and may inject per-document context
through their own comparators module. The core never imports a category.
"""
from __future__ import annotations

from typing import Callable

from .comparators_common import (
    amount_comparator,
    date_comparator,
    exact_comparator,
    identifier_comparator,
    integer_comparator,
    name_comparator,
    rate_set_comparator,
)

Comparator = Callable[[object, object, dict], str]
# returns one of: "correct" | "incorrect" | "hallucination"

REGISTRY: dict[str, Comparator] = {
    "exact": exact_comparator,
    "name": name_comparator,
    "identifier": identifier_comparator,
    "date": date_comparator,
    "amount": amount_comparator,
    "rate_set": rate_set_comparator,
    "integer": integer_comparator,
}


def get_comparator(name: str) -> Comparator:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown comparator {name!r}; known: {sorted(REGISTRY)}") from None
