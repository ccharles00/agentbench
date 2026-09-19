# Build Spec: Global Invoice Extraction Benchmark for the Agentic Era

Working name: **[PROJECT_NAME]** (owner to choose; use a placeholder in code and config)

> **For the coding agent reading this (e.g. Claude Code):** This document is the full brief. Part A explains *why* the project exists and the strategic constraints behind design decisions. Part B is the technical specification. Part C covers the build schedule, acceptance criteria, and working rules. Read all three before writing code. When something here conflicts with what you find in current vendor documentation (API names, pricing, model names), trust the current documentation and note the discrepancy for the owner.

---

## PART A — Strategy and Context

### A1. The big idea

A growing share of software purchasing will be done by AI agents acting for people and companies. Agents don't browse deal sites or respond to marketing. They choose tools based on machine-readable specs, verified performance, and price. Today there is no neutral, trustworthy source of "which tool actually does this job best, for what cost" that an agent can query.

The long-term vision is a marketplace for the agentic era (an "AppSumo for agents"), but the marketplace is **not** what we build first. We start with the asset a marketplace would need and can't easily copy: **neutral, verified, task-specific performance data**, exposed both to humans (website) and to agents (JSON API + MCP server).

### A1b. Invoices are the first category, not the product

The invoice benchmark is the MVP and proof of concept. **The actual product is a category-agnostic verification layer for agent purchasing**: a repeatable way to (1) create tasks with known correct answers, (2) run competing tools on them, (3) score and publish results for humans and agents, and eventually (4) route agent purchases, guarantees, and pooled demand based on those results.

Invoices were chosen first because they are objectively gradable, commercially important, under-tested globally, and match the owner's expertise. Expected future categories include:
- **Other document extraction:** receipts, bank statements, purchase orders, customs and shipping documents, contracts, forms and survey responses.
- **Other services agents buy with gradable outputs:** transcription, translation, handwriting OCR, web scraping and data enrichment, address and identity verification, geocoding, PII redaction.
- **Later:** services judged by rubric or human review, where ground truth is weaker.

**Design consequence:** everything except the invoice-specific plugin must be category-agnostic (see B0). When a design choice would make adding a second category harder, choose the other option. But do not build a second real category in v1, and do not add speculative features: generality should live in clean interfaces, not extra functionality.

### A2. Why this wedge (decisions already made)

Several marketplace concepts were considered:

| Concept | Verdict for v1 |
|---|---|
| Reverse group-buy: agents pool structured purchase intent, vendors bid on cohorts | Future layer. Needs demand volume we don't have yet. |
| **Proof-of-use: tools evaluated on real tasks, results published as verified evidence** | **Chosen.** Can launch with zero users; creates value on day one. |
| Resale market for completed agent work (cached research/datasets) | Interesting, later. |
| Bonded outcomes: services carry escrowed guarantees | Future layer. Needs capital; becomes priceable once we have failure-rate data. |
| Policy-matched procurement for enterprises | Future layer. Long sales cycles. |

Reasoning:
- **Start from the seller side.** Tool vendors already know agents are calling their APIs and have no way to prove they're the best choice. They have a problem today. Most buyers don't yet.
- **A benchmark needs no network to be useful.** We run the tests ourselves. Published results attract both vendors (who want to win or be retested) and builders (who want answers).
- **The data compounds.** Every test run adds to a history competitors can't buy later. The later marketplace layers (pooled demand, guarantees, procurement matching) become features on top of this data.

### A3. The first category: global invoice extraction

**Extraction of structured data from invoices across the world's languages, scripts, number formats, currencies, calendars, and tax systems.**

Why this niche:
- Objectively gradable: fields have right answers, so no voting or subjective judgment is needed.
- Commercially important: accounts-payable automation is one of the most common agent use cases, and cross-border trade paperwork is messy.
- Under-tested: most public comparisons use clean English-language US-style invoices. Tools fail in interesting and costly ways elsewhere (e.g., reading `1.234` as 1.234 instead of 1,234; reading a Thai Buddhist-calendar year 2569 literally; confusing ¥ for yen vs yuan).
- Owner advantage: the owner is a veteran coder (~50 years, founder of a survey software company) with an MBA in international finance, so he can judge what "correct" means for tax and currency handling.

Positioning headline for launch: **"Your agent's invoice extractor works in English. Here's how it does on the rest of the world's commerce."**

### A4. Analogues and how we differ

- **LMArena** (LLM leaderboard): proves neutral public rankings can become a real business. But it relies on crowdsourced human preference votes, suited to subjective chat quality. We use ground truth, so results are harder to dispute and need no crowd to bootstrap.
- **Artificial Analysis** (API speed/price/quality benchmarks): the closer analogue. We differ by ranking *tools on one specific job*, reporting *cost per correct result*, and serving *agent buyers* via API/MCP.
- **Lesson from criticism of LMArena:** vendors game public leaderboards (e.g., privately testing many variants, publishing the best). Our defense: public generator + public sample for reproducibility, but official rankings scored on a **private held-out set** regenerated periodically.

### A5. Neutrality is the moat (and must be real)

Big platforms (model labs, cloud providers, payment companies) could build something similar. Our defense is neutrality plus depth in messy, specific categories they won't bother with. Neutrality only counts if it's verifiable, so the following are hard rules, published on the site:

1. No pay-for-placement. Rankings are determined only by measured results.
2. Every tool is tested with the same documents, the same settings policy, and (for LLMs) the same prompt.
3. Methodology, generator code, scoring code, and public sample are open source.
4. Every result is labeled with the tool version/model ID and test date.
5. Any commercial relationship with a vendor (sponsored retests, listings) is disclosed on that vendor's page.
6. Retest requests are accepted from anyone, and retests run on a published schedule for all tools, not on demand for payers only.
7. A public corrections log records every error we fix.

### A6. Business roadmap (for context; do NOT build beyond Phase 0 now)

- **Phase 0 (this weekend):** benchmark + static site + JSON API + MCP server. Free.
- **Phase 1 (weeks 2–8):** validate. Signals: traffic, shares, vendor contacts, retest requests, API/MCP usage.
- **Phase 2 (monetize):** disclosed sponsored retests; verified vendor listings with sandbox links; paid API tier for heavy agent usage; private custom benchmarks run on a company's own documents (likely strongest early revenue).
- **Phase 3 (marketplace):** pooled demand from agents querying with requirements; bonded/guaranteed outcomes priced from our failure-rate data; procurement-policy matching; purchase routing with take rate.
- **Additional categories later:** receipts, bank statements, purchase orders, customs documents, and form/survey response extraction (an area the owner knows deeply).

### A7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Nobody cares about the category | Launch fast and cheap; measure response within 2 weeks; pivot category if needed. |
| Vendor terms of service restrict publishing benchmarks | Owner reviews each vendor's ToS before publishing (see C4). Exclude any vendor that prohibits it, and note the exclusion publicly. |
| Critics dismiss synthetic data as unrealistic | Realistic templates per country; native-speaker spot check of samples; later add a small set of real public-domain invoices. |
| Ground-truth bugs undermine credibility | Automated self-checks in the generator (see B2.8); corrections log. |
| Vendors overfit to the public set | Official scores on private held-out set; show public vs private gap. |
| Small sample sizes | Report counts and 95% Wilson confidence intervals; don't overclaim. |
| API costs | Budget cap in config; cost estimate and explicit confirmation before any paid run; response caching. |
| Big platform builds a competitor | Neutrality, openness, and category depth; move fast. |

---

## PART B — Technical Specification

### B0. Core engine vs category plugins

Split the codebase into a **category-agnostic core** and **category plugins**.

The core contains: the harness runner, caching, cost control and retries, the scoring framework (a registry of field comparators, metrics, confidence intervals, breakdowns by arbitrary dimensions), the results format, the site generator, the static API builder, and the MCP server.

A category plugin lives in `/categories/<category_id>/` and provides:
- `category.yaml`: id, display name, description, field list with a comparator type per field, dimensions used for breakdowns, and the headline metric.
- A task source: a synthetic generator with ground truth, or a loader for curated real data.
- Adapters (or adapter configurations) for tools in that category.
- Category-specific normalizers and comparators (e.g., currency-precision amounts, calendar-aware dates), registered with the core.
- Prompt(s) for LLM baselines.
- Category-specific site copy: headline finding, methodology section.

Rules:
- The core must never import from a category plugin.
- Include a tiny test-only stub at `categories/_example/` (three fake tasks, one trivial comparator, one fake adapter) that runs through the full pipeline in the test suite. This proves the core is genuinely category-agnostic at almost no cost.
- Site, API, and MCP server all treat categories as a first-class concept even though v1 has only one.

### B1. System overview

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Generator   │──▶│   Harness    │──▶│   Scorer     │──▶│  Publisher   │
│ synthetic    │   │ vendor       │   │ normalize +  │   │ static site, │
│ invoices +   │   │ adapters,    │   │ score +      │   │ JSON API,    │
│ ground truth │   │ cache, cost  │   │ aggregate    │   │ llms.txt     │
└──────────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                                                │
                                                         ┌──────▼───────┐
                                                         │  MCP server  │
                                                         │ (reads JSON  │
                                                         │  API)        │
                                                         └──────────────┘
```

Everything is batch/offline except the MCP server. The website and API are **static files** (no backend server needed for v1).

### B2. Component 1: Synthetic invoice generator

#### B2.1 Approach
- Invoices are defined as structured data (ground truth) first, then rendered through per-country HTML templates to PDF, then optionally degraded to images.
- Render with **headless Chromium via Playwright** (print to PDF). Chromium handles complex script shaping, right-to-left text, and mixed-direction text correctly; ReportLab and similar libraries do not handle Arabic/Indic shaping well.
- Use **Google Noto fonts** (Noto Sans, Noto Sans CJK, Noto Naskh Arabic, Noto Sans Devanagari, Noto Sans Thai, Noto Sans Hebrew) bundled in the repo or installed in setup, so rendering is reproducible.
- Generation is **fully deterministic from a seed**. Same seed produces byte-identical ground truth and visually identical documents.

#### B2.2 Country coverage (v1)

Core set (build all of these):

| Code | Why it's included |
|---|---|
| US | Baseline; MM/DD dates; state sales tax; routing + account numbers |
| GB | VAT 20%; DD/MM dates; IBAN |
| DE | Comma decimals, period thousands; USt 19%/7%; reverse-charge wording; IBAN |
| IN | Lakh/crore grouping (1,00,000); GST split CGST+SGST vs IGST; GSTIN; Devanagari + English mixing |
| CN | Chinese script; VAT fapiao style; ¥ ambiguity (CNY) |
| JP | Japanese script; ¥ (JPY, zero decimals); Reiwa era dates; consumption tax 10%/8%; registration number |
| KR | Korean script; KRW zero decimals; VAT 10% |
| BR | Portuguese; comma decimals; NF-e/DANFE-style layout (simplified); multiple taxes |
| MX | Spanish; IVA 16%; RFC; CLABE bank account |
| SA | Arabic RTL with LTR numbers; option of Arabic-Indic digits; VAT 15%; QR code present |
| AE | Arabic/English bilingual; VAT 5%; TRN; AED |
| ID | Indonesian; space or period thousands; PPN VAT; IDR large amounts, typically no decimals |
| TH | Thai script; **Buddhist calendar year** (Gregorian + 543); VAT 7% |

Stretch set (only if time permits): KW or BH (three-decimal currency: KWD/BHD), IL (Hebrew RTL, ILS), RU or KZ (Cyrillic), IR or AF (Persian calendar and Persian digits).

**Tax rates:** keep them in a config table. Exact current statutory rates matter less than internal consistency, because we are measuring extraction, not tax compliance. Still, use rates that are realistic, and add a comment for the owner to verify them.

#### B2.3 Variation dimensions

Each generated invoice samples from these dimensions (respecting what's realistic for the country):

- **Script and language:** native only, native + English bilingual, or English-only (e.g., a Chinese supplier invoicing in English).
- **Number format:** country-native, or foreign (cross-border invoices often mix conventions).
- **Digits:** Western digits, or Arabic-Indic/Persian digits where applicable.
- **Currency:** local currency, or USD/EUR for cross-border; sometimes two currencies shown (e.g., amount plus converted amount); symbol vs ISO code vs both.
- **Dates:** native format and calendar (Japanese era, Thai Buddhist year, Persian calendar in stretch set); ambiguous DD/MM vs MM/DD cases deliberately included (e.g., 04/03).
- **Tax treatment:** tax-exclusive vs tax-inclusive pricing; single vs multiple rates; reverse charge (zero tax with a note); withholding tax line where realistic.
- **Layout:** 2–3 template variants per country (header positions, table styles, logo placement, totals box location).
- **Line items:** 1–25 items; some long descriptions that wrap; occasional multi-page invoices.

#### B2.4 Degradation levels

Each base invoice is emitted in up to four variants:

1. `clean_pdf` — vector PDF with text layer.
2. `scan` — rasterized, slight rotation (±3°), mild noise, 200 DPI, grayscale, **no text layer**.
3. `bad_scan` — heavier noise, blur, lower resolution (~150 DPI), stamp overlapping some text, JPEG artifacts.
4. `phone_photo` — perspective warp, uneven lighting/shadow, background margin, JPEG.

Use PyMuPDF for rasterizing and Pillow/OpenCV for effects. The **Augraphy** library (document augmentation) may be used if convenient. Degradation must also be seeded and deterministic.

#### B2.5 Ground-truth schema

One JSON file per base invoice, shared by all its degradation variants.

```json
{
  "doc_id": "JP-0007",
  "country": "JP",
  "language": ["ja", "en"],
  "script": ["Jpan", "Latn"],
  "dimensions": {
    "calendar": "japanese_era",
    "number_format": "native",
    "digits": "western",
    "tax_mode": "exclusive",
    "cross_border": false,
    "template": "jp_b"
  },
  "fields": {
    "vendor_name": "株式会社サンプル商事",
    "vendor_tax_id": "T1234567890123",
    "invoice_number": "INV-2026-00417",
    "invoice_date": "2026-03-04",
    "due_date": "2026-04-30",
    "currency": "JPY",
    "subtotal": "120000",
    "tax_total": "12000",
    "total": "132000",
    "tax_rates": ["10"],
    "payment_account": null,
    "line_item_count": 6
  },
  "rendered_strings": {
    "invoice_date": "令和8年3月4日",
    "total": "¥132,000"
  }
}
```

Rules:
- Dates: ISO 8601 Gregorian, regardless of how rendered.
- Currency: ISO 4217 code.
- Amounts: decimal **strings** with exactly the currency's minor-unit precision (JPY 0 places, USD 2, KWD 3). Never floats.
- `payment_account`: normalized IBAN (no spaces, uppercase), or CLABE, or null when not present.
- `rendered_strings`: exactly how key values appear on the document, used for self-checks and the failure gallery.

#### B2.6 Scored fields (v1)

`vendor_name`, `vendor_tax_id`, `invoice_number`, `invoice_date`, `due_date`, `currency`, `subtotal`, `tax_total`, `total`, `tax_rates`, `payment_account`, `line_item_count`.

Line-item-level extraction is out of scope for v1 (count only).

#### B2.7 Dataset size and splits

- **Public split:** ~100 base invoices (≈8 per core country), published seed, all degradation variants. Committed to repo or downloadable.
- **Private split:** same size and distribution, secret seed stored only in owner's environment (never committed). Official leaderboard uses the private split.
- The site shows both scores; a large public-vs-private gap for a tool gets flagged as possible overfitting.
- Version datasets: `dataset_version: 2026.1`, etc.

#### B2.8 Generator self-checks (required)

Fail generation loudly if any check fails:
- `subtotal + tax_total == total` (with correct handling of tax-inclusive pricing).
- Line items sum to subtotal.
- For `clean_pdf`: extract the text layer and confirm every `rendered_strings` value is present.
- Every date in `fields` is valid and round-trips through the calendar conversion.
- Amount precision matches the currency's minor units.
- Output a contact sheet (thumbnail grid) per country for quick human visual review.

### B3. Component 2: Harness and vendor adapters

#### B3.1 Adapter interface

```python
class ExtractorAdapter(Protocol):
    tool_id: str            # e.g. "aws_textract_expense"
    display_name: str
    def version(self) -> str: ...          # model ID / API version tested
    def estimate_cost(self, doc: DocFile) -> Decimal: ...   # USD
    def extract(self, doc: DocFile) -> RawResult: ...       # raw vendor response + timing
    def to_canonical(self, raw: RawResult) -> CanonicalFields: ...  # map to schema
```

`to_canonical` maps vendor output to our field names **without** fixing values (no correcting dates or number formats on the vendor's behalf). Only unit/label mapping is allowed. Anything the vendor didn't return is `null`.

#### B3.2 Candidate tools for v1 (pick ~6)

Dedicated document-AI services (verify current product names and pricing in their docs):
- AWS Textract (expense/invoice analysis)
- Google Cloud Document AI (invoice parser)
- Azure AI Document Intelligence (prebuilt invoice model)
- One or two specialist startups with public APIs (e.g., Mindee or similar)

General-purpose LLMs given the same extraction prompt (use current flagship model IDs from config, not hardcoded):
- An Anthropic Claude model
- An OpenAI model
- A Google Gemini model

Owner decides the final list. Make adding a new adapter a single-file change.

#### B3.3 Standard LLM prompt

All LLM adapters use one shared prompt and the same JSON schema, stored in `prompts/extract_v1.md`, versioned. The prompt instructs the model to return only JSON with the field names in B2.6, ISO dates, ISO currency codes, and plain decimal amounts. Documents are passed natively (PDF or image input) where supported. Temperature 0 (or the provider's most deterministic setting). The prompt text is published on the methodology page.

#### B3.4 Harness behavior

- **Caching:** store raw responses under `cache/{tool_id}/{tool_version}/{doc_sha256}.json`. Rescoring never re-calls APIs.
- **Cost control:** before a run, print estimated total cost per tool and overall; require `--confirm` or interactive yes. Hard stop at `BUDGET_USD` from config.
- **Retries:** exponential backoff on transient errors; record permanent failures as failures (they count against the tool).
- **Timing:** record wall-clock latency per call.
- **Secrets:** API keys from environment variables / `.env` (gitignored). Never log keys.
- **Concurrency:** modest parallelism per vendor, respecting rate limits.
- CLI: `bench run --tools all --split public --variants all --dry-run`

### B4. Component 3: Normalization and scoring

#### B4.1 Normalization (applied identically to ground truth and predictions)
- Strings: Unicode NFKC, casefold, trim, collapse internal whitespace, strip trailing punctuation.
- `vendor_name`: compare against the name as printed (native script). If the document shows both native and Latin names, either is accepted (ground truth stores alternates).
- IDs (`vendor_tax_id`, `invoice_number`, `payment_account`): remove spaces and hyphens, uppercase.
- Amounts: parse to Decimal; must equal ground truth exactly at the currency's precision. A vendor returning `1.234` for one thousand two hundred thirty-four is wrong.
- Dates: must equal ISO Gregorian date exactly. Swapped day/month is wrong.
- `tax_rates`: set comparison of numeric rates.
- Null handling: ground truth null + prediction null = correct; ground truth null + prediction non-null = incorrect (hallucination); ground truth non-null + prediction null = incorrect (miss). Track hallucinations separately.

#### B4.2 Metrics
Per tool, overall and broken down by country, script, calendar, number format, degradation variant, and field:
- Field accuracy (% of fields correct)
- **Document exact-match rate** (% of documents with all fields correct) — the headline metric
- **Cost per fully correct document** (total cost / number of exact-match documents) — the buyer metric
- Mean cost per document
- Latency p50 and p95
- API failure rate
- Hallucination rate (non-null answers where the truth is null)
- 95% Wilson confidence intervals and sample counts shown next to every percentage

#### B4.3 Outputs
`results/{dataset_version}/{split}/summary.json`, `by_dimension.json`, `per_doc.jsonl` (every field comparison), `failures.jsonl` (for the gallery).

### B5. Component 4: Static website

Generated from results JSON. Keep it simple: a static site generator of the agent's choice (Astro, or Python + Jinja templates + a little vanilla JS). Host on Cloudflare Pages or GitHub Pages.

Pages:
1. **Leaderboard** — sortable table: tool, doc exact-match %, field accuracy %, cost per correct doc, latency p50, tested version, test date. Toggle public/private split.
2. **Heatmap** — tools × countries (and tools × degradation) colored by exact-match rate.
3. **Failure gallery** — the viral asset. Each card: document image (cropped to the relevant region if feasible), field name, expected value, what the tool returned, rendered string as printed. Filter by tool, country, field. Pre-select striking examples for the home page (e.g., lakh misread, Buddhist year taken literally, decimal/thousands confusion).
4. **Tool pages** — one per tool: strengths/weaknesses by dimension, version history, disclosures.
5. **Methodology** — dataset design, splits, scoring rules, the exact LLM prompt, known limitations.
6. **Neutrality policy** — the rules in A5, verbatim.
7. **API & MCP docs** — how agents query the data.
8. **Corrections log.**

Design: clean, fast, fully readable on mobile, dark mode support. No trackers beyond privacy-friendly analytics (e.g., a cookieless option) so the owner can measure traction.

### B6. Component 5: Agent-facing JSON API (static)

Served as static files from the same site, namespaced by category:
- `/api/v1/index.json` — available categories, last updated
- `/api/v1/categories/{category_id}/index.json` — dataset versions, tools, dimensions
- `/api/v1/categories/{category_id}/leaderboard.json` — summary for all tools
- `/api/v1/categories/{category_id}/tools/{tool_id}.json` — full profile with per-dimension scores
- `/api/v1/categories/{category_id}/dimensions/{dimension}/{value}.json` — e.g., `.../invoices/dimensions/country/IN.json`
- `/llms.txt` — plain-language description of the site, API, and how an agent should use it to choose a tool

Every response includes `dataset_version`, `test_date`, `split`, and a link to methodology.

### B7. Component 6: MCP server

A small MCP server (Python or TypeScript; publishable as a package) that fetches the static JSON API and exposes tools:

- `list_categories()` — categories benchmarked (v1: invoices only)
- `list_tools(category)` — tools benchmarked, versions, test dates
- `recommend_tool(category, constraints)` — generic version of the recommender below; constraints are category dimensions plus cost and accuracy thresholds
- `get_leaderboard(split="private", dimension=None, value=None)`
- `recommend_extractor(countries: list, degradation: str | None, max_cost_per_doc_usd: float | None, min_exact_match: float | None)` — returns ranked candidates with scores, confidence intervals, and cost, plus a one-sentence rationale and a methodology link
- `get_failures(tool_id, country=None, field=None, limit=5)` — examples of mistakes

It never claims certainty beyond the data: responses include sample sizes and confidence intervals.

### B8. Repository layout

```
/core
  /harness        run.py, cache.py, cost.py, adapter_base.py
  /scoring        registry.py, comparators_common.py, metrics.py, aggregate.py
/categories
  /invoices       category.yaml
                  generator/ (templates/, fonts/, countries/*.py, calendars.py, render.py, degrade.py, selfcheck.py)
                  adapters/*.py, comparators.py, prompts/extract_v1.md, site_copy.md
  /_example       test-only stub proving the core is category-agnostic
/site             static site source
/api-build        builds /api/v1 JSON + llms.txt from results
/mcp-server       MCP server package
/results          versioned outputs (public split committed; private split results committed, private documents NOT)
/data/public      public split documents + ground truth
/tests            unit tests (calendars, number parsing, normalization, scoring)
config.yaml       tools enabled, budget, dataset version, tax-rate table
.env.example      required environment variables (no real keys)
README.md         setup, commands, how to add a tool, how to reproduce results
LICENSE           open-source license for code (owner to choose, e.g. MIT or Apache-2.0); data license (e.g. CC BY 4.0)
```

Language: Python 3.11+ for generator, harness, and scoring. `uv` or `pip` with a lock file. A single `make` or `just` file with commands: `generate`, `selfcheck`, `run`, `score`, `build-site`, `build-api`, `serve`.

---

## PART C — Build Plan and Working Rules

### C1. Weekend schedule with acceptance criteria

**Milestone 1 (Friday evening): Generator**
- Core countries render in clean PDF with correct scripts, RTL, and calendars.
- Ground-truth JSON produced; all self-checks pass.
- Degradation variants produced.
- Contact sheets generated for visual review.
- ✅ Done when: `make generate && make selfcheck` passes for the public split, and the owner has eyeballed contact sheets.

**Milestone 2 (Saturday): Harness + scoring**
- At least 3 adapters working end-to-end (target 6).
- Dry run shows cost estimate; confirmed run completes within budget.
- Scoring produces all metrics in B4.2 with unit tests for normalization edge cases (lakh grouping, comma decimals, three-decimal currencies, era/Buddhist dates, null handling).
- ✅ Done when: `results/.../summary.json` exists for public and private splits and the numbers pass a manual spot check of 10 random documents.

**Milestone 3 (Sunday): Site + API + MCP**
- All pages in B5 built from results; failure gallery has at least 20 curated examples.
- Static API and `llms.txt` generated.
- MCP server runs locally and answers `recommend_extractor` correctly.
- Deployed to a public URL.
- ✅ Done when: a fresh visitor can understand the headline finding within 10 seconds on the home page, and an agent using the MCP server gets a sensible recommendation.

**Stretch (only after all milestones):** stretch countries, additional adapters, per-field crop images in the gallery.

### C2. Explicit non-goals for v1

Do not build: user accounts, payments, vendor dashboards, submission portals, databases, a dynamic backend, marketplace mechanics, line-item-level scoring, or real (non-synthetic) customer documents.

### C3. Working rules for the coding agent

1. Work milestone by milestone; commit at the end of each with a clear message.
2. **Ask the owner before any action that spends money** (API runs beyond a small smoke test) and before exceeding `BUDGET_USD`.
3. Never commit secrets, the private seed, or private split documents.
4. Verify current vendor API names, request formats, model IDs, and pricing from official documentation rather than memory; record the docs URL and date in each adapter's docstring.
5. Prefer simple, readable code over cleverness; the owner will maintain it.
6. Write tests for all normalization and calendar logic; these are where credibility lives.
7. If a design decision is ambiguous, pick the option that keeps results more reproducible and neutral, and note it in `DECISIONS.md`.
8. Keep a running `TODO_OWNER.md` of things only the owner can do (see C4).
9. Keep the core category-agnostic (B0). Invoice-specific logic belongs only in `categories/invoices/`.
10. Work autonomously within each milestone. Stop and ask the owner only at these checkpoints: the end of each milestone; before spending money; when an account, credential, or legal/ToS judgment is needed; and when a decision would be hard to reverse. Otherwise, make a reasonable choice, record it in `DECISIONS.md`, and keep going.

### C4. Owner checklist (human tasks)

- [ ] Choose project name and domain.
- [ ] Create vendor accounts and API keys; add to `.env`.
- [ ] **Review each vendor's terms of service for restrictions on publishing benchmarks.** Exclude any that prohibit it and note this on the methodology page.
- [ ] Verify tax rates in the config table look realistic.
- [ ] Arrange a quick native-speaker spot check of 2–3 sample invoices per script (e.g., a small paid review on a freelance platform).
- [ ] Generate and securely store the private seed.
- [ ] Choose code and data licenses.
- [ ] Approve the API spending budget.

### C5. Launch checklist (Monday)

- [ ] Home page leads with the single most striking finding plus 3 failure-gallery examples.
- [ ] Email each vendor its results, methodology link, and an open invitation to request a retest (send at or just before publication).
- [ ] Post a Show HN.
- [ ] LinkedIn post from the owner (international finance + founder credibility).
- [ ] Share in agent-builder and document-AI communities (Reddit, Discord servers, X).
- [ ] Publish the MCP server to a public MCP directory/registry.
- [ ] Set up analytics and a simple contact/retest-request email address.

### C6. Success signals to watch (first 2 weeks)

- Vendors reaching out (positive or negative): the strongest signal.
- Retest requests.
- Inbound links and shares of failure-gallery examples.
- API and MCP usage.
- Requests for benchmarks on other document types or on private company documents (early signal for paid custom benchmarks).

If signals are weak after 2 weeks, reuse the harness and generator pattern on a different category before investing further.
