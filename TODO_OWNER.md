# TODO_OWNER

Things only the owner can do or decide. See build spec C3.8 / C4.

## 🔒 LAUNCH GATE — Milestone 3 is built; deploy is blocked on you

- [x] ~~Vendor ToS review (spec C4)~~ — **Decided 2026-09-20:** AWS and the
  Gemini API terms are clear (no benchmark restriction). OpenAI's "No
  Publicity" clause is ambiguous as applied to independent benchmark
  results, and the owner has accepted that risk rather than seeking
  further legal clearance or excluding OpenAI — see DECISIONS.md #26.
  **This was the only blocker.** The deploy workflow
  (.github/workflows/deploy-site.yml) is still manual-trigger ONLY —
  triggering it is now purely the owner's call, whenever ready.
- [ ] Choose project name (leaning AssayMark) and confirm before launch
  branding; placeholder `agentbench` everywhere it's user-visible. Not a
  hard blocker — can launch on `agentbench` and rename later.

## Milestone 3 review (Textract investigation follow-ups)

Owner decisions queued from the 2026-09-20 Textract investigation
(#23 fixed the mapping bugs; these two policies remain):

- [ ] **Q1 — Locale-conventional dates.** Current rule (#22): a non-ISO date
  counts only when self-evident (a part >12). Textract returns dates in the
  document's own convention (`10.02.2025` on a German invoice = correct
  value, ambiguous form) and scores wrong — 158 correct-in-locale date
  reads across the public split. Option B: accept a date that is correct
  under the document's country convention (applied symmetrically to all
  tools; active misreads still fail). Agent recommendation: B — it extends
  #22's principle that the document's own packaging isn't a wrong value.
  With B + Q2-strict, Texact field accuracy rises ~4-5pp; exact-match is
  unaffected by Q1 (currency gates it).
- [ ] **Q2 — Currency-from-symbol.** Textract never returned `currency`
  (0/910 though the schema supports it), so exact-match 0.0% is structurally
  unreachable for it under strict scoring. Option: allow deriving currency
  from a currency symbol in a returned amount ("$" + US → USD; ¥ needs
  country). Agent recommendation: **keep strict** — deriving currency from
  symbols crosses B3.1's "no fixing on the vendor's behalf" line (¥/CNY-JPY
  genuinely requires external knowledge). Publish 0.0% with the structural
  explanation on the methodology page and let field accuracy carry the
  comparison. If you prefer the symbol rule, it applies to every tool
  symmetrically and needs re-scoring (free, from cache).

## Vendor ToS notes (owner research, 2026-09-20)

- AWS Service Terms: benchmark disclosure permitted; no prior consent
  required, methodological transparency suffices (we have it). **Clear.**
- Gemini API Additional Terms of Service (the AI Studio/developers terms
  that actually apply here, confirmed distinct from Google Cloud's): no
  benchmark-disclosure clause at all. Only restriction is "competitive
  use" (developing competing models, reverse-engineering weights) —
  doesn't apply to measuring task performance. **Clear.**
  (Google Cloud terms DO require prior written consent for benchmark
  disclosure — stays relevant only if Google Document AI becomes tool #4.)
- **OpenAI — decided 2026-09-20, see DECISIONS.md #26.** The OpenAI
  Services Agreement's "No Publicity" clause (Section 10) is ambiguous as
  applied to independent benchmark results (no explicit carve-out, unlike
  AWS). Owner reviewed and chose to proceed, naming OpenAI/GPT-5.6-terra
  on the leaderboard the same as AWS and Google. Risk accepted knowingly,
  not overlooked — full clause text and reasoning in DECISIONS.md.

## Milestone 2 review

- [x] ~~Top up the OpenAI credit balance~~ — **Done 2026-09-20:** last 13
  private docs run (0 failures); OpenAI private complete at 455/455,
  61.8% exact-match. Results committed.

## Milestone 1 review

- [ ] **Eyeball the contact sheets** in `data/public/contact_sheets/` — now at
  review resolution (1000px thumbnails, 2-column grids). Flag anything
  unrealistic; `make generate` regenerates in minutes.

## Choices and accounts (build spec C4)

- [ ] **Project name: leaning AssayMark** (runners-up: AgentAssay, AssayLab,
  VerdictBench, OpenAssay — all checked live against a registrar, not guessed).
  "Assay" itself is fully squatted on every good TLD; these compounds are open.
- [ ] **Domain: don't buy yet.** Launch Milestone 3 on the free Cloudflare
  Pages/GitHub Pages subdomain (spec B5) and read the Launch Checklist signals
  (C5/C6 — vendor contact, retest requests, traffic, API/MCP usage) before
  spending anything. If it's worth continuing after that, `.io` is roughly half
  the price of `.ai` for the same name (~$35/yr promo vs. ~$90+/yr, since `.ai`'s
  registry — Anguilla — charges a much higher wholesale fee and often forces a
  2-year minimum). Placeholder in code stays `agentbench` until a name is
  actually registered.
- [ ] Create vendor accounts and API keys; add to `.env` (template in
  `.env.example`) — needed for Milestone 2 smoke runs.
- [ ] **Review each vendor's terms of service for restrictions on publishing
  benchmarks.** Exclude any that prohibit it; note exclusions on the
  methodology page (M3).
- [ ] **Verify the tax-rate table in `config.yaml` looks realistic** (spec B2.2).
  Internal consistency is what matters for scoring, but rates should be
  plausible: US state sales tax, GB 20, DE 19/7, IN GST slabs, CN 13/9/6,
  JP 10/8, KR 10, BR ICMS + PIS 1.65/COFINS 7.6, MX IVA 16 (retención ISR 10),
  SA 15, AE 5, ID PPN 11 (12% luxury from 2025 — confirm current treatment),
  TH 7.
- [ ] Arrange a native-speaker spot check of 2–3 sample invoices per script
  (Arabic, Devanagari, Thai, CJK ×3) — contact sheets are a good review artifact
  to send.
- [x] ~~Generate and securely store the private seed~~ — **Done 2026-09-19:**
      `private_seed.txt` created; private split generated and self-checked
      clean (104 docs). Keep the seed file out of any shared backup.
- [x] ~~Choose code and data licenses~~ — **Decided 2026-09-19:** code MIT,
  public dataset CC BY 4.0. See `LICENSE`, `DATA_LICENSE`, `DECISIONS.md`.
- [ ] Approve the API spending budget (`budget_usd` in `config.yaml`) before any
  Milestone 2 paid run.

## Strategic notes

- [ ] **Federal/enterprise procurement as a Phase 2 buyer.** TechCrunch (2026-09-19) on
  Vals AI ($40M Series A, a16z, 8x revenue growth) confirms their buyer base includes
  federal agencies evaluating AI model acquisitions. Government AP automation and
  customs/procurement paperwork extraction is already on our "later categories" list
  (BUILD_SPEC A1b) — worth treating federal/enterprise procurement teams as a plausible
  Phase 2 custom-benchmark customer, not just individual document-AI vendors. No action
  needed for v1; revisit when scoping Phase 2 monetization.
