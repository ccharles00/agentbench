# Extraction Prompt v1 (spec B3.3)

Version: 1 — 2026-09-19. All LLM adapters use this prompt verbatim, at
temperature 0 (or the provider's most deterministic setting), passing the
document natively (PDF or image input) where supported. The prompt text is
published on the methodology page.

Field definitions mirror the ground truth exactly (DECISIONS.md #4, #18):
`payment_account` means IBAN or CLABE only; `tax_total` is taxes charged,
never withholding.

---

You are extracting structured data from an invoice. The invoice may be in any
language, script, or layout, from any country: read it carefully.

Return ONLY a JSON object — no prose, no markdown fences — with exactly these
keys. Use `null` for any field that is not printed on the document. Never
guess or invent values.

```json
{
  "vendor_name": "string — the seller's name exactly as printed",
  "vendor_tax_id": "string — the seller's tax registration number as printed (VAT no., GSTIN, RFC, tax ID, etc.)",
  "invoice_number": "string — the invoice/document number as printed",
  "invoice_date": "string — date in ISO 8601 (YYYY-MM-DD), converted to the Gregorian calendar if the document uses another calendar (e.g. Japanese era, Thai Buddhist year)",
  "due_date": "string — payment due date in ISO 8601 (YYYY-MM-DD), or null if not printed",
  "currency": "string — ISO 4217 currency code (e.g. JPY, CNY, INR, EUR). Resolve symbols: ¥ may mean JPY or CNY — decide from the document's country or explicit code",
  "subtotal": "string — net amount (before tax) as a plain decimal number at the currency's precision, no thousands separators (e.g. \"1234.56\")",
  "tax_total": "string — total taxes CHARGED (VAT/GST/IVA/PPN/sales tax), plain decimal. NEVER include amounts withheld by the buyer (retenciones/retention). If tax is included in prices, compute the tax portion",
  "total": "string — grand total payable as printed (after any withholding), plain decimal",
  "tax_rates": "array of strings — the tax rates applied, as plain decimals (e.g. [\"19\"] or [\"9\",\"9\"] for a split tax); [] if none",
  "payment_account": "string — the payee IBAN (no spaces) or Mexican CLABE, or null if the document shows none or shows other payment details (e.g. a US bank routing/account pair)",
  "line_item_count": "integer — number of line items on the invoice"
}
```

Rules:
- Amounts: convert the printed format to a plain decimal. "1.234,56" (German)
  means one thousand two hundred thirty-four and 56/100 → "1234.56".
  "1,00,000.00" (Indian lakh grouping) → "100000.00". Preserve the printed
  value exactly; do not round.
- Dates: convert to Gregorian ISO. 令和8年3月4日 → "2026-03-04". A Thai year
  2569 → 2026. Keep day/month order straight: read the document's convention.
- Currency: if two currencies are shown, report the currency the total is
  denominated in.
- Do not normalize tax IDs beyond removing spaces and hyphens and uppercasing.
- Output the JSON object only.
