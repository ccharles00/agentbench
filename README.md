# Global Invoice Extraction Benchmark (working name: `agentbench` — placeholder)

Neutral, verified, task-specific performance data for AI agent tools. v1 category:
**extraction of structured data from invoices across languages, scripts, number
formats, currencies, calendars, and tax systems.** See
`agent leaderboard - BUILD_SPEC.md` for the full brief.

Status: **Milestone 1 (generator) complete** — harness + scoring (M2) and
site/API/MCP (M3) are next.

## What is here

```
core/            category-agnostic CLI + config (harness/scoring land in M2)
categories/
  invoices/      the v1 category plugin
    generator/   synthetic invoice generator: countries, templates, calendars,
                 money formatting, degradation, self-checks
    category.yaml
  _example/      (M2) test-only stub proving the core is category-agnostic
data/public/     committed public split: ground truth + clean PDFs
                 (scan/bad_scan/phone_photo rasters regenerate deterministically)
site/ api-build/ mcp-server/ results/   (Milestones 2–3)
tests/           unit tests for calendars, money, IDs, schema invariants
```

## Quickstart

Requires Python 3.11+ and GNU make (on Windows, Git Bash + `winget install ezwinports.make`).

```bash
make setup        # venv + locked dependencies + Chromium for Playwright
make fonts        # download Noto fonts pinned in fonts.lock (SHA256-verified)
make generate     # generate the public split (data/public)
make selfcheck    # run the B2.8 self-checks
make test         # unit tests
make run          # cost estimate only (CONFIRM=1 make run executes paid runs)
make score        # score cached results into results/<split>
make build        # build the static site + agent JSON API + llms.txt
make serve        # serve the site at http://localhost:8080
```

The MCP server: `python mcp-server/server.py` (stdio; reads the built site
API — run `make build` first). Deploy is ToS-gated: the GitHub Pages
workflow is manual-trigger only until the owner's vendor ToS review
completes (TODO_OWNER.md).

Milestone 1 acceptance: `make generate && make selfcheck` passes for the public
split, and the owner has reviewed the contact sheets in
`data/public/contact_sheets/` (one per country, plus one degradation-variants
sheet).

## Determinism

Generation is fully deterministic from the published seed in `config.yaml`
(`public_seed: 20260919`). Each document's RNG is derived as
`SHA256(split:seed:doc_id)`, so the same seed regenerates byte-identical ground
truth and visually identical documents. The **private split** uses a secret seed
from `PRIVATE_SEED` (env var) or `private_seed.txt` — never committed:

```bash
make generate SPLIT=private
```

## Dataset (v1)

- 13 core countries × 8 base invoices = 104 documents (US GB DE IN CN JP KR BR MX SA AE ID TH)
- Up to 4 variants each: `clean_pdf`, `scan` (200 DPI grayscale, rotated),
  `bad_scan` (blur/noise/stamp/JPEG), `phone_photo` (perspective/lighting/margin)
- Variation dimensions per spec B2.3: language mode (native/bilingual/English),
  number format (western/european/indian/space), digits (western/Arabic-Indic),
  calendars (Gregorian/Japanese era/Thai Buddhist), tax modes (exclusive,
  inclusive, reverse charge, GST splits, PIS/COFINS, retención), layouts (a/b/c
  + simplified fapiao), cross-border invoices, deliberate DD/MM↔MM/DD ambiguity
- Ground truth schema per spec B2.5: ISO dates, ISO currency, decimal-string
  amounts at minor-unit precision, `rendered_strings` for self-checks/failures
- `data/public/manifest.json` lists every document and its variant files

## Adding a country or a tool

- **Country:** add `categories/invoices/generator/countries/<cc>.py` (data pools
  + `make_scenarios()`), list it in `config.yaml` (`countries`, `tax_rates`), add
  the code to `COUNTRY_MODULES` in `generator/generate.py`. The builder handles
  all money math and schema assembly.
- **Tool (M2):** drop a single adapter file into `categories/invoices/adapters/`.

## License

Code is MIT (see `LICENSE`). The public dataset (`data/public/` — ground truth
and documents) is CC BY 4.0 (see `DATA_LICENSE`). The private split is never
published.

## Working rules recap (spec C3)

Ask the owner before anything that spends money; never commit secrets, the
private seed, or private-split documents; verify vendor specifics against
current docs; decisions land in `DECISIONS.md`, owner actions in `TODO_OWNER.md`.
