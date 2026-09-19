# Decisions Log

Ambiguous design decisions made by the coding agent, per build spec C3.7.
Each entry: the decision, why, and what it affects.

## Milestone 1 (generator)

1. **Project name placeholder `agentbench`.** Owner chooses the real name/domain
   (C4). It appears only in `config.yaml` and this repo's copy; easy to rename.

2. **Fonts are installed in setup, not committed** (spec B2.1 allows either).
   `scripts/fetch_fonts.py` pins a `google/fonts` commit + SHA256 per file in
   `categories/invoices/generator/fonts.lock` (committed); the font binaries are
   gitignored. Keeps the repo light and rendering reproducible.

3. **IDR canonical amounts use ISO 4217 minor units (2 decimals), e.g.
   `"163137275.23"`, while documents display whole rupiah (`Rp163.137.275`).**
   The spec's schema rule is "exactly the currency's minor-unit precision"; the
   display convention stays realistic. Vendors returning whole-rupiah integers
   without decimals must normalize to the canonical form — same rule as
   trailing-zero handling for any currency.

4. **`payment_account` only stores IBANs and CLABEs (spec B2.5).** US routing +
   account numbers and Japanese bank lines are printed on documents for realism
   but ground truth is `null`, because the schema defines no normalized form for
   them. Consequence (intentional, documented for the methodology page):
   `payment_account` means "IBAN or CLABE"; an extractor returning a US account
   number there is scored as a hallucination. The LLM prompt (M2) must define
   the field the same way.

5. **Multi-page invoices:** degraded variants are emitted as one image per page
   (`..._scan_p1.png`, `..._scan_p2.png`, ...); `clean_pdf` stays a multi-page
   PDF. `manifest.json` lists every file per variant. 13 of 104 public docs are
   multi-page.

6. **Public split commits ground truth + clean PDFs; scan/bad_scan/phone_photo
   rasters are gitignored** (≈238 MB regenerable from the seed in minutes).
   Spec B2.7 allows "committed to repo or downloadable"; deterministic
   regeneration is the download.

7. **`tax_rates` ground truth = the percentage rates printed in the tax/summary
   area, in document order, duplicates kept.** Indian CGST+SGST invoices store
   `["9","9"]` (two printed lines); Brazilian docs with PIS/COFINS store e.g.
   `["18","1.65","7.6"]`; the Mexican retención doc stores `["16","10"]`;
   reverse-charge docs store `["0"]` (a 0% line is printed). Scoring does set
   comparison (B4.1), so duplicates only matter for display.

8. **Withholding (Retención ISR) on two MX documents:** `total = subtotal + IVA
   − retención` and `tax_total = IVA − retención`, so the B2.8 identity
   `subtotal + tax_total == total` still holds. This is a deliberately hard,
   realistic case; flagged in the methodology copy so vendors don't read it as a
   ground-truth bug.

9. **`rendered_strings` only contains values literally printed as single
   strings.** Omitted where not printed: `subtotal` on tax-inclusive documents
   (Japanese 内税 style shows only total + included tax), `tax_total` when taxes
   print as multiple lines (CGST+SGST, PIS/COFINS, retención) whose sum never
   appears as one number. The B2.8 text-layer check verifies exactly what is
   printed.

10. **Reverse charge** is a `tax_mode` dimension value (`reverse_charge`), rates
    0, with the German statutory note printed on the document.

11. **Simplified fapiao layout for CN layout-`c` documents** (red band, buyer/
    seller boxes, per-item rate and tax columns, 价税合计 with Chinese uppercase
    amount). It includes a printed due-date row (real fapiao don't have one) so
    every scored field stays extractable and fairly gradable.

12. **Text-layer self-check tolerates RTL extraction scrambling.** Chromium
    renders Arabic correctly, but PDF extraction returns RTL runs in scrambled
    visual order (Arabic-Indic digit runs come out reversed; attached
    abbreviations get split). After exact / reversed / diacritic-loose matching,
    the check falls back to: every numeric token's digit sequence present on a
    single extracted line (forward or reversed), plus at least one letter of the
    value present (tofu detector). LTR documents still require exact matches.

13. **Layout variants (2–3 per country, spec B2.3) are three CSS layout classes
    (header placement, table style, totals box, logo placement) plus the CN
    fapiao special — one Jinja template, not 30 files.** Template ids in ground
    truth follow the spec's shape (`jp_b`, `us_a`, ...).

14. **Packaging: plain pip + committed `requirements.lock`** (uv isn't installed
    on the owner's machine). `make setup` installs from the lock; the venv lives
    in `.venv/` (gitignored).

15. **Generated IBANs/CLABEs carry real check digits** (ISO 13616 mod-97; CLABE
    weights 3/7/1), validated in unit tests and self-checks. Tax IDs are
    format-plausible but not checksum-verified (not scored; noted as a
    limitation).

16. **Deliberate ambiguity coverage:** every country's 8-doc plan includes
    ambiguous dates (day ≤ 12) on ≥1 doc; IN has three lakh-range docs; ID has
    two space-grouping docs; SA has three Arabic-Indic digit docs; ¥ appears
    symbol-only on most CN/JP docs (the currency field is where extractors must
    disambiguate CNY vs JPY).

## Owner decisions

Unlike the numbered list above (ambiguous calls the coding agent made per spec
C3.7), the items below are owner decisions from the build spec's C4 checklist,
made explicitly by the owner and recorded here for the same reason: so the
next agent working in this repo doesn't have to guess or re-litigate them.

17. **License, 2026-09-19: code MIT, public dataset CC BY 4.0.** Spec C4 left
    this to the owner; `TODO_OWNER.md` had suggested CC BY 4.0 for the dataset
    as a starting point, which is what shipped. MIT was already the repo's
    placeholder and needed no change — it's the standard low-friction choice
    for a generator/scoring/MCP codebase the project wants vendors and other
    builders to actually adopt and extend (spec A5.3: open methodology is part
    of the neutrality moat). CC BY 4.0 on `data/public/` (ground truth +
    documents) matches common practice for open benchmark datasets — reuse and
    redistribution are fine, including commercially, as long as it's
    attributed. Copyright holder is Oak Mountain Digital LLC, the entity that
    owns this project. See `LICENSE` and `DATA_LICENSE`. The private split
    (secret-seed documents/ground truth) is never published, so no license
    applies to it — see `DATA_LICENSE`'s own note.
