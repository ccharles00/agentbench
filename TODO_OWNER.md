# TODO_OWNER

Things only the owner can do or decide. See build spec C3.8 / C4.

## Milestone 1 review (now)

- [ ] **Eyeball the contact sheets** in `data/public/contact_sheets/` — one per
  country plus `*_variants.png` sheets showing scan/bad_scan/phone_photo
  degradation. Flag anything that looks unrealistic (names, addresses, layouts,
  tax lines, date formats). Regenerate any time with `make generate`.

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
- [ ] Generate and securely store the **private seed**: e.g.
  `python -c "import secrets; print(secrets.randbits(64))"` → `private_seed.txt`
  (gitignored) or the `PRIVATE_SEED` env var. Then `make generate SPLIT=private`.
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
