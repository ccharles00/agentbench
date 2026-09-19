"""Per-document scoring and dimension aggregation (spec B4).

`score_document` compares one prediction (one degradation variant of one
document) against ground truth, honoring DECISIONS.md #19: (doc, field)
pairs listed in `unscored_fields` are excluded from every denominator,
including document exact-match.
"""
from __future__ import annotations

from .registry import get_comparator


def score_document(gt: dict, prediction: dict | None, variant: str,
                    fields: dict, field_context) -> tuple[list[dict], bool, bool]:
    """Compare one prediction against ground truth.

    fields: {field_name: comparator_name} from category.yaml.
    field_context: callable(gt) -> dict merged into each comparator's ctx.
    prediction: {field: value} (missing keys count as null). None = API failure.

    Returns (comparison rows, exact_match, api_failed).
    """
    rows: list[dict] = []
    unscored = set(gt.get("unscored_fields") or [])
    ctx_base = field_context(gt) if field_context else {}
    doc_exact = True

    if prediction is None:
        # API failure: every scored field is a miss; the doc is not exact
        for field in fields:
            if field in unscored:
                continue
            rows.append(_row(gt, variant, field, None, "incorrect"))
        return rows, False, True

    for field, comp_name in fields.items():
        if field in unscored:
            continue
        truth = gt["fields"].get(field)
        pred = prediction.get(field)
        ctx = dict(ctx_base)
        if field == "vendor_name":
            ctx["alternates"] = (gt.get("field_alternates") or {}).get(field, [])
        outcome = get_comparator(comp_name)(truth, pred, ctx)
        rows.append(_row(gt, variant, field, pred, outcome))
        if outcome != "correct":
            doc_exact = False

    return rows, doc_exact, False


def _row(gt: dict, variant: str, field: str, pred, outcome: str) -> dict:
    return {
        "doc_id": gt["doc_id"],
        "variant": variant,
        "field": field,
        "truth": gt["fields"].get(field),
        "prediction": pred,
        "outcome": outcome,
        "rendered": (gt.get("rendered_strings") or {}).get(field),
    }


def dimension_values(gt: dict, variant: str, dimensions: list[str]) -> dict:
    """The breakdown coordinates of one (doc, variant) pair."""
    out = {}
    gdims = gt.get("dimensions") or {}
    for dim in dimensions:
        if dim == "variant":
            out[dim] = variant
        elif dim in ("language", "script"):
            v = gdims.get(dim)
            out[dim] = "+".join(v) if isinstance(v, list) else v
        else:
            out[dim] = gdims.get(dim)
    return out
