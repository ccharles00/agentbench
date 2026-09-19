# Handoff: repo status and shared-tree workflow

Written 2026-09-19 by a Claude Code session (Sonnet 5) working alongside the
GLM 5.3 / zcode session that built Milestone 1. Read this before your next
commit or push.

## Repo location

Same working directory as always: `F:\Users\Chris\Websites\AgentMarketplace`.
It now has a GitHub remote it didn't have before:

```
origin  https://github.com/ccharles00/agentbench.git
```

Public repo, under Chris's personal GitHub account (`ccharles00`), not any
org. `main` is the only branch, currently at commit `e333bbe`, on top of the
Milestone 1 commit (`08a1288`).

## You're sharing one local git index/HEAD with at least one other agent

This directory isn't a worktree — it's the same checkout multiple sessions
commit to. That means:

- Don't `git add -A` / `git add .` — stage explicit filenames only
  (`git add -- path/to/file`), so you never accidentally stage or commit
  something another session touched but hasn't finished.
- Run `git status` before committing, and `git log --oneline -5` before
  pushing, so you can see if HEAD moved since you last looked.
- Before `git push`, do a `git pull --rebase` (or confirm `git status` says
  "up to date") in case another session pushed in the meantime — avoids a
  diverged-history mess.
- No `git reset --hard`, `git clean -f`, or `git checkout .` without checking
  `git status` first — could discard another session's uncommitted work.

## Push credentials

`gh auth status` shows this machine logged in as `ccharles00` with `repo`
scope, credential helper `store` (file-based, user-level) — any process
running as this Windows user should inherit the same stored HTTPS
credentials, so `git push` should just work. Worth a one-time sanity check
rather than assuming.

## What changed since Milestone 1

- **License decided** (spec C4, an owner call — Chris made it explicitly):
  code MIT, public dataset CC BY 4.0. New `DATA_LICENSE` file at repo root;
  `LICENSE` now has the real copyright holder (Oak Mountain Digital LLC)
  instead of a placeholder; `README.md` has a License section;
  `TODO_OWNER.md`'s licensing line is checked off; `DECISIONS.md` has a new
  "Owner decisions" section (#17) with the rationale — read that before
  touching licensing again.
- **The repo is now public and live**, not just local. This raises the
  stakes on the existing `.gitignore` rules (`.env`, `private_seed.txt` /
  `PRIVATE_SEED`, `data/private/`) — they were always required by spec
  C3.3/B2.7, but a slip is now immediately visible on GitHub, not just a
  local mistake. Matters most starting Milestone 2, when vendor API keys
  and the harness show up — double-check `git status` before every commit
  once that work begins.
- Project name is still **undecided** — keep using the `agentbench`
  placeholder in code/config until Chris confirms one (the "leaning
  AssayMark" note in `TODO_OWNER.md` is still open, not settled).
- Domain: **don't buy one yet** — per `TODO_OWNER.md`, Milestone 3 launches
  on a free GitHub Pages/Cloudflare Pages subdomain, and a real domain waits
  for traction signals (C5/C6).

## Queued from the 2026-09-19 review of DECISIONS.md

Chris reviewed the decisions log (via a Claude session that checked each
entry against the ground-truth files) and made three owner decisions —
`DECISIONS.md` #18, #19, #20. Read those entries first; the "why" lives
there. This is the implementation list. Nothing has been scored yet, so the
public split can be regenerated in place — **keep `dataset_version: 2026.1`**,
no bump needed.

**Decided — implement before Milestone 2 scoring:**

1. **#18 withholding — now two components, not one.** In `build.py` (the
   `retention` block, ~L291): stop subtracting from `tax_total`; keep
   subtracting from `total`; write the summed amount to a new
   `fields.withholding_total` (decimal string, `null` when no withholding);
   don't add retention rates to `tax_rates`. The MX retention scenario needs
   **both** ISR retention (10% of subtotal) **and** IVA retention (2/3 of the
   IVA charged = 10.6667% of subtotal) — `withholding_total` is their sum,
   printed as two separate lines ("IVA retenida (2/3)", "ISR retenida
   (10%)"), each its own `TaxLine` subtracted from `total`. Self-check
   identity: `subtotal + tax_total − (withholding_total or 0) == total`.
   Add dimension `withholding` (bool) to ground truth and to `category.yaml`
   `dimensions`. Do **not** add `withholding_total` to `category.yaml`
   `fields`. In `countries/mx.py`, the two retention scenarios get persona
   física vendors (person's name, 13-char RFC). Update `selfcheck.py`'s
   `_KNOWN_EXTRA_RATES` accordingly (see item 6 below).
2. **#19 unscored fields.** Ground truth gains `unscored_fields: []`. Set
   `["payment_account"]` on docs that *print* payment details the schema
   can't normalize (US routing/account, JP bank lines); leave it empty and
   `payment_account: null` on docs that print no payment details at all. The
   M2 scorer must exclude listed `(doc, field)` pairs from every denominator,
   including document exact-match.
3. **#20 fapiao + tax IDs.** Remove the due-date row from the `cn_c` layout
   in `templates/base.html.j2`; `due_date: null` on those docs. In `ids.py`:
   CN USCC per GB 32100-2015 (first char 1/5/9/Y, 6-digit division code,
   no I/O/Z/S/V, mod-31 check char); IN GSTIN (state code + PAN + entity +
   `Z` + mod-36 check); MX RFC with a valid YYMMDD date, 12/13 chars by
   entity type. Draw vendor name + tax ID as one stable pair per vendor.
   Self-check validates the three check characters; unit tests per algorithm.

**Also found — fix unless you have a reason not to (log-vs-data mismatches
and gaps, not owner decisions):**

4. **#3 is not what the data does.** ID docs render sen
   (`Rp146.970.518,23`), and 6 of 8 have fractional amounts and unit prices.
   Indonesian invoices show whole rupiah; PPN rounds to whole rupiah.
   Generate whole-rupiah amounts for ID and check JP/KR the same way. Then
   correct entry #3's text to match.
5. **Units are sampled independently of descriptions** — ID-0001 sells a
   24-port switch and monthly accounting by the ream (`"unit": "rim"`). Pair
   unit with description category in every country's pools.
6. **Dimension gaps in `category.yaml`:** `language_mode` is written into
   every ground-truth file but not declared, so it can't be broken down —
   add it. Add `ambiguous_date` (true when the rendered invoice date is a
   numeric day/month form with day ≤ 12 and day ≠ month; 38 of 104 public
   docs qualify) so the headline finding can be sliced from results. Scope
   `selfcheck.py`'s `_KNOWN_EXTRA_RATES` per country instead of globally.
7. **Rasters aren't byte-reproducible across machines** (Chromium/Pillow/
   OpenCV/JPEG versions). Ground truth is; documents are only "visually
   identical" (spec B2.1). For M3, attach the public-split rasters to a
   GitHub Release tagged per `dataset_version` rather than relying on
   regeneration — note for whoever does M3, no M1/M2 action.

**Downstream obligations to carry into M2/M3** (from #4, #7, #8, #11, #18–20):
the LLM prompt must define `payment_account` ("IBAN or CLABE") and
`tax_total` (taxes charged only) exactly as the ground truth does; the
methodology page must state the withholding definition, the unscored-field
rule, the fapiao null due date, and the weaker RTL self-check on SA/AE (#12).
