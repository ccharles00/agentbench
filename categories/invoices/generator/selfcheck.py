"""Self-checks for a generated split — fail loudly (spec B2.8).

Checks, per document:
  1. schema: required keys present, scored fields exactly per B2.6
  2. amounts: decimal strings at exactly the currency's minor-unit precision
  3. identity: subtotal + tax_total == total (inclusive pricing handled by
     construction — items are gross and subtotal = total - tax_total)
  4. line items sum to the right total for the tax mode
  5. dates: valid ISO, round-trip through the native calendar
  6. tax rates parse and are plausible for the country's config table
  7. payment_account: valid IBAN (mod-97) or CLABE where present
  8. clean_pdf text layer contains every rendered_strings value
  9. every variant file listed in the manifest exists and is non-empty
Plus: manifest/ground-truth agreement and contact sheets present.
"""
from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

from core.config import data_dir

from . import ids, money
from .calendars import round_trip as calendar_round_trip
from .model import GT_FIELDS

_KNOWN_EXTRA_RATES = {"0", "1.65", "7.6", "10"}  # reverse charge, PIS, COFINS, MX retención
MAX_REPORTED = 25


class Problems:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, doc_id: str, msg: str) -> None:
        self.items.append(f"{doc_id}: {msg}")

    def ok(self) -> bool:
        return not self.items


# --------------------------------------------------------------------------- #
# text-layer matching
# --------------------------------------------------------------------------- #

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    return " ".join(s.split())


def _loose(s: str) -> str:
    s = _norm(s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _digit_norm(s: str) -> str:
    return _loose(s).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))


def _digit_seq(s: str) -> str:
    return "".join(ch for ch in _digit_norm(s) if ch.isdigit())


def text_contains(haystack: str, needle: str) -> bool:
    """Is the rendered value present in the extracted text layer?

    Chromium renders Arabic correctly but PDF text extraction returns RTL runs
    in scrambled visual order — Arabic-Indic digit runs come out reversed, and
    attached Arabic abbreviations get split. So after exact / reversed /
    diacritic-loose matching fails, fall back to: every numeric token of the
    value has its digit sequence present (forwards or reversed) on a single
    extracted line, and at least one letter of the value exists at all (catches
    tofu/dropped glyphs). See DECISIONS.md.
    """
    n, h = _norm(needle), _norm(haystack)
    if n in h or n[::-1] in h:          # exact, or simple RTL visual order
        return True
    if _loose(needle) in _loose(haystack):
        return True
    nl, hl = _digit_norm(needle), _digit_norm(haystack)
    numbers = re.findall(r"[0-9][0-9.,/]*", nl)
    if not numbers:
        return False
    line_seqs = [seq for line in haystack.splitlines()
                 if (seq := _digit_seq(line))]
    for tok in numbers:
        tseq = _digit_seq(tok)
        if not tseq:
            continue
        if not any(tseq in ls or tseq in ls[::-1] for ls in line_seqs):
            return False
    letters = [c for c in nl if c.isalpha()]
    return not letters or any(c in hl for c in letters)


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #

def check_gt_schema(gt: dict) -> None:
    missing = [k for k in ("doc_id", "country", "language", "script", "dimensions",
                           "fields", "line_items", "rendered_strings") if k not in gt]
    if missing:
        raise ValueError(f"ground truth missing keys: {missing}")
    if set(gt["fields"]) != set(GT_FIELDS):
        raise ValueError(f"fields must be exactly {GT_FIELDS}, got {sorted(gt['fields'])}")


def check_amounts(gt: dict, doc_id: str, problems: Problems) -> None:
    currency = gt["fields"]["currency"]
    minor = money.MINOR_UNITS[currency]
    for key in ("subtotal", "tax_total", "total"):
        raw = gt["fields"][key]
        try:
            d = Decimal(raw)
        except InvalidOperation:
            problems.add(doc_id, f"{key} is not a decimal string: {raw!r}")
            continue
        if minor == 0 and "." in raw:
            problems.add(doc_id, f"{key} has decimals but {currency} has 0 minor units")
        elif minor > 0 and len(raw.partition(".")[2]) != minor:
            problems.add(doc_id,
                         f"{key}={raw!r} must have exactly {minor} decimals for {currency}")


def check_identity(gt: dict, doc_id: str, problems: Problems) -> None:
    f = gt["fields"]
    try:
        subtotal, tax_total, total = (Decimal(f[k]) for k in ("subtotal", "tax_total", "total"))
    except InvalidOperation:
        return
    if subtotal + tax_total != total:
        problems.add(doc_id, f"identity fails: {subtotal} + {tax_total} != {total}")
    items_sum = sum(Decimal(li["amount"]) for li in gt["line_items"])
    mode = gt["dimensions"]["tax_mode"]
    expected = total if mode in ("inclusive",) else subtotal
    if items_sum != expected:
        problems.add(doc_id,
                     f"line items sum {items_sum} != {expected} (tax_mode={mode})")
    if mode == "reverse_charge" and tax_total != 0:
        problems.add(doc_id, "reverse charge doc must have tax_total 0")
    if len(gt["line_items"]) != f["line_item_count"]:
        problems.add(doc_id, "line_item_count does not match line_items length")


def check_dates(gt: dict, doc_id: str, problems: Problems) -> None:
    from datetime import date as date_cls
    calendar = gt["dimensions"]["calendar"]
    for key in ("invoice_date", "due_date"):
        raw = gt["fields"][key]
        try:
            d = date_cls.fromisoformat(raw)
        except ValueError:
            problems.add(doc_id, f"{key} is not ISO 8601: {raw!r}")
            continue
        try:
            if calendar_round_trip(d, calendar) != d:
                problems.add(doc_id, f"{key} calendar round-trip changed the date")
        except ValueError as exc:
            problems.add(doc_id, f"{key} calendar round-trip failed: {exc}")


def check_tax_rates(gt: dict, doc_id: str, tax_table: dict, problems: Problems) -> None:
    country = gt["country"]
    table = tax_table.get(country, {})
    allowed: set[Decimal] = set()
    if isinstance(table, dict):            # US state table
        allowed |= {Decimal(str(v)) for v in table.values()}
    else:
        allowed |= {Decimal(str(v)) for v in table}
    for extra in _KNOWN_EXTRA_RATES:
        allowed.add(Decimal(extra))
    for rate_str in gt["fields"]["tax_rates"]:
        try:
            rate = Decimal(rate_str)
        except InvalidOperation:
            problems.add(doc_id, f"tax rate not parseable: {rate_str!r}")
            continue
        if rate in allowed or rate * 2 in allowed:   # rate*2 covers GST half-rates
            continue
        problems.add(doc_id, f"tax rate {rate_str} not plausible for {country} ({allowed})")


def check_payment_account(gt: dict, doc_id: str, problems: Problems) -> None:
    acct = gt["fields"]["payment_account"]
    if acct is None:
        return
    if ids.iban_is_valid(acct):
        return
    if len(acct) == 18 and acct.isdigit() and ids.clabe_check_digit(acct[:17]) == acct[17]:
        return
    problems.add(doc_id, f"payment_account {acct!r} is neither a valid IBAN nor a valid CLABE")


def check_rendered_strings(gt: dict, pdf_path: Path, doc_id: str, problems: Problems) -> None:
    import pymupdf as fitz
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    for key, rendered in gt["rendered_strings"].items():
        if not text_contains(text, rendered):
            problems.add(doc_id,
                         f"rendered_strings[{key}]={rendered!r} not found in clean PDF text layer")


def check_files(entry: dict, base: Path, doc_id: str, problems: Problems) -> None:
    for variant, files in entry["variants"].items():
        if not files:
            problems.add(doc_id, f"variant {variant} has no files")
        for rel in files:
            p = base / rel
            if not p.exists() or p.stat().st_size == 0:
                problems.add(doc_id, f"missing or empty file: {rel}")
    expected_variants = {"clean_pdf", "scan", "bad_scan", "phone_photo"}
    missing = expected_variants - set(entry["variants"])
    if missing:
        problems.add(doc_id, f"missing variants: {sorted(missing)}")


def run(config: dict, split: str = "public") -> None:
    base = data_dir(split)
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"no manifest at {manifest_path} — run generate first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    problems = Problems()
    gt_paths_seen = set()
    for entry in manifest["documents"]:
        doc_id = entry["doc_id"]
        gt_path = base / entry["ground_truth"]
        gt_paths_seen.add(gt_path)
        if not gt_path.exists():
            problems.add(doc_id, f"missing ground truth file {gt_path.name}")
            continue
        try:
            gt = json.loads(gt_path.read_text(encoding="utf-8"))
            check_gt_schema(gt)
        except ValueError as exc:
            problems.add(doc_id, f"schema: {exc}")
            continue
        check_amounts(gt, doc_id, problems)
        check_identity(gt, doc_id, problems)
        check_dates(gt, doc_id, problems)
        check_tax_rates(gt, doc_id, config["tax_rates"], problems)
        check_payment_account(gt, doc_id, problems)
        check_files(entry, base, doc_id, problems)
        pdf_path = base / entry["variants"]["clean_pdf"][0]
        if pdf_path.exists():
            check_rendered_strings(gt, pdf_path, doc_id, problems)

    stray = {p for p in (base / "ground_truth").glob("*.json")} - gt_paths_seen
    for p in sorted(stray):
        problems.add("manifest", f"ground truth file not in manifest: {p.name}")

    countries = {e["country"] for e in manifest["documents"]}
    sheets_dir = base / "contact_sheets"
    for country in sorted(countries):
        if not (sheets_dir / f"{country}.png").exists():
            problems.add("contact_sheets", f"missing contact sheet for {country}")

    n_docs = len(manifest["documents"])
    if problems.ok():
        print(f"SELF-CHECK OK — {n_docs} documents, all checks passed "
              f"(split={split}, dataset_version={manifest['dataset_version']})")
        return
    print(f"SELF-CHECK FAILED — {n_docs} documents, {len(problems.items)} problem(s):")
    for line in problems.items[:MAX_REPORTED]:
        print(f"  - {line}")
    if len(problems.items) > MAX_REPORTED:
        print(f"  ... and {len(problems.items) - MAX_REPORTED} more")
    raise SystemExit(1)
