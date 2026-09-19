# Decisions Log

Two kinds of entries: ambiguous design decisions made by the coding agent
(spec C3.7, the numbered Milestone sections) and owner decisions (spec C4,
the "Owner decisions" section). Each entry: the decision, why, and what it
affects. A superseded entry stays in place with a pointer to what replaced
it — never delete history here.

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
   *Superseded 2026-09-19 by #19: printed-but-unnormalizable payment details
   are now unscored for that doc, not counted as hallucination.*

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
   *Amended 2026-09-19 by #18: withholding rates (the MX `"10"`) are no longer
   stored in `tax_rates`.*

8. **Withholding (Retención ISR) on two MX documents:** `total = subtotal + IVA
   − retención` and `tax_total = IVA − retención`, so the B2.8 identity
   `subtotal + tax_total == total` still holds. This is a deliberately hard,
   realistic case; flagged in the methodology copy so vendors don't read it as a
   ground-truth bug.
   *Superseded 2026-09-19 by #18: withholding is split out of `tax_total` into
   its own field.*

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
    *Superseded 2026-09-19 by #20: the due-date row is removed; `due_date` is
    null on fapiao-style docs.*

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
    *Amended 2026-09-19 by #20: CN, IN and MX tax IDs get real structure and
    check characters; the rest stay format-plausible.*

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

18. **Withholding, 2026-09-19: `tax_total` is taxes charged only; withholding
    gets its own field.** Supersedes #8, amends #7. Verified in the data:
    MX-0004 and MX-0007 carry `tax_rates ["16","10"]` and a `tax_total` equal
    to 6% of subtotal, on documents that print "IVA 16%" and "Retención ISR
    10%" as separate lines. In CFDI terms those are *impuestos trasladados*
    (tax the vendor charges) and *impuestos retenidos* (income tax the buyer
    withholds from the vendor) — separate blocks because they are different
    things. Every AP system and every LLM returns the IVA amount as the tax
    total; scoring that as wrong, and showing it in the failure gallery, would
    read to any Mexican accountant as the benchmark getting the tax wrong — in
    the exact category (cross-border tax handling) the project claims as its
    edge. The B2.8 identity drove the old definition; the identity changes,
    the definition doesn't. Decision:
    - `fields.tax_total` = sum of taxes charged (IVA, VAT, GST, PIS/COFINS…).
    - New `fields.withholding_total`: decimal string at currency precision,
      `null` when the document has no withholding. **Not a scored field in
      v1** (not added to `category.yaml` `fields`), so document-exact-match
      denominators don't change; revisit for v2 once there is a reason.
    - `fields.tax_rates` = charged-tax rates only; withholding rates excluded.
    - Self-check identity becomes
      `subtotal + tax_total − (withholding_total or 0) == total`.
    - New boolean dimension `withholding` (ground truth + `category.yaml`), so
      results can be sliced on it.
    - Retention documents use **persona física vendors** (a person's name,
      13-character RFC). ISR 10% retention applies to individuals billing
      companies for professional services, not to the S.A. de C.V. / S.C.
      vendors those two docs currently have.
    - *Amended same day, before implementation:* **IVA retention is generated
      too, not simplified away.** In practice ISR retention on professional
      fees paid by a company to an individual is accompanied by IVA
      retention — the recipient withholds two-thirds of the IVA charged
      (16% × 2/3 = 10.6667% of subtotal) alongside the 10% ISR retention.
      `withholding_total` = ISR retention + IVA retention (two components,
      one field — the field stays unscored in v1, so no schema growth from
      splitting it). The document prints both as separate lines ("IVA
      retenida (2/3) −X.XX", "ISR retenida (10%) −Y.YY"), each subtracted
      from `total` in `build.py`'s retention block. `tax_rates` is unaffected
      (still charged-only, i.e. `["16"]`) — retention rates were already
      excluded from it. Self-check identity is unchanged:
      `subtotal + tax_total − (withholding_total or 0) == total`; only what
      feeds `withholding_total` grows from one term to two.
    - Keep two retention docs in the MX plan; the methodology page explains
      the field definitions. The M2 LLM prompt defines `tax_total` the same
      way (and does not ask for `withholding_total`).

19. **Unscored fields, 2026-09-19: a printed value the schema cannot normalize
    is excluded from scoring, not counted as a hallucination.** Supersedes #4.
    US documents print routing + account numbers and JP documents print bank
    name/branch/account; ground truth stores `null` because the schema has no
    normalized form, and #4 scored a tool that reads them correctly as
    hallucinating. That corrupts the hallucination-rate metric (B4.2), whose
    purpose is to catch fabrication: a tool that reads the printed account on
    all 8 US docs would show ~8% hallucination for being right, and unlike an
    LLM the dedicated document-AI services cannot be prompted around it.
    Decision:
    - Ground truth gains `unscored_fields: [...]` (usually empty). A
      `(document, field)` pair listed there is excluded from every
      denominator: field accuracy, hallucination rate, miss rate, and
      document exact-match (computed over that document's scored fields).
    - Applied to `payment_account` on documents that print payment details
      with no normalized form. Documents that print **no** payment details keep
      `payment_account: null` **and stay scored** — that is the real
      hallucination test, and the generator must distinguish the two cases.
    - `payment_account` still means "IBAN or CLABE" (#4's definition stands).
    - Per-document results carry the unscored list; the methodology page
      states the rule. Defining normalized forms for US/JP details was
      rejected for v1: more schema surface, and there is no standard for how
      a US routing + account pair should be returned.

20. **Fapiao and tax IDs, 2026-09-19: no invented due-date row; CN/IN/MX tax
    IDs are structurally valid.** Supersedes #11, amends #15. Real fapiao
    carry no due date; #11 added one so every field would be extractable, but
    B4.1 already handles absent fields (null + null correct, null + value
    hallucination), so a null `due_date` is both more realistic and a more
    informative test — does the tool invent one? As-is, 3 of 8 CN docs carry a
    row a Chinese reviewer spots instantly (A7, "synthetic data is
    unrealistic"). Decision:
    - Remove the due-date row from the `cn_c` layout; `due_date: null` on
      those docs, scored under the normal null rules.
    - Generate structurally valid tax IDs where the format has a defined
      structure or check character: CN unified social credit code
      (GB 32100-2015 — first char 1/5/9/Y, 6-digit division code, alphabet
      without I/O/Z/S/V, mod-31 check char); IN GSTIN (2-digit state code +
      PAN + entity code + Z + mod-36 check char); MX RFC (3 or 4 letters, a
      **valid YYMMDD date**, homoclave; 12 chars for personas morales, 13 for
      físicas). Verified failures in current data: CN-0001
      `H1QW9U96QL54NB7U8K` (bad first char, non-numeric division code); every
      MX RFC has an impossible date (`VWH527641YL2` → month 76). Tools that
      validate these identifiers — common for Chinese and Indian extractors —
      would reject correct reads, an unfair failure mode. Other countries' IDs
      stay format-plausible (US EIN has no check digit); #15 amended.
    - Vendor identity is a stable pair: name and tax ID are drawn together,
      so the same company never appears with different tax IDs (MX has
      "Distribuidora del Norte S.A. de C.V." on three docs with three RFCs).
    - Self-checks validate the CN/IN/MX check characters; unit tests cover
      each algorithm.
