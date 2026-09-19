"""Generic invoice builder (spec B2.3, amended by DECISIONS.md #18-#20).

Country modules (countries/*.py) supply data pools and format hooks in a
CountrySpec plus a per-document DOC_PLAN; this module owns ALL money math,
tax-mode handling, language/script selection, and ground-truth assembly so
the same invariants hold for every country (spec B2.8):

- exclusive pricing:  items are net; subtotal + tax_total − withholding == total
- inclusive pricing:  items are gross; subtotal == total − tax_total
- reverse charge:     rate 0 with a note; tax_total == 0
- tax_total is charged taxes only; buyer-side retention (ISR/IVA retenida)
  lives in withholding_total and prints as its own lines (#18)
- every amount quantized to the currency's minor units (whole units for IDR)

Determinism: every random choice comes from the per-document RNG; vendor tax
IDs are derived from the vendor NAME (stable_rng), so one company always has
one ID (#20).
"""
from __future__ import annotations

import base64
import io
import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable

from . import ids as idgen
from . import money, words
from .model import Invoice, LineItem, TaxLine, Vendor

Q1 = Decimal("1")

ENGLISH_LABELS = {
    "title": "INVOICE", "invoice_no": "Invoice No.", "invoice_date": "Invoice Date",
    "due_date": "Due Date", "bill_to": "Bill To", "description": "Description",
    "qty": "Qty", "unit_price": "Unit Price", "amount": "Amount", "subtotal": "Subtotal",
    "total": "Total", "payment_terms": "Payment Terms", "payment_account": "Account / IBAN",
    "amount_in_words": "Amount in Words",
}

# Buyer-side pools for cross-border invoices.
FOREIGN_CUSTOMERS = (
    "Global Sourcing GmbH", "Acme Manufacturing Inc.", "Nordic Retail AB",
    "Pacific Rim Imports LLC", "Euro Office Depot B.V.", "Atlas Procurement Ltd.",
    "Andes Distribution S.A.", "Gulf Supplies FZE", "Orion Logistics Pte. Ltd.",
    "Continental Retail Group",
)
FOREIGN_ADDRESSES = (
    ("Industriestrasse 42", "60314 Frankfurt", "Germany"),
    ("1200 Market Street", "Philadelphia, PA 19107", "United States"),
    ("Vasagatan 18", "111 20 Stockholm", "Sweden"),
    ("8 Harbour Road", "Wanchai", "Hong Kong"),
    ("De Ruijterkade 6", "1013 AA Amsterdam", "Netherlands"),
    ("25 Old Broad Street", "London EC2N 1HN", "United Kingdom"),
)

FALLBACK_ENGLISH_ITEMS = (
    "Office chairs, mesh back, ergonomic (set of 4)",
    "Monthly IT maintenance — servers and network, on-site and remote support",
    "Freight services, palletized goods, door to door",
    "Software license — annual subscription, 10 seats",
    "Paper A4 80gsm, carton of 10 reams",
    "Accounting and bookkeeping services — monthly",
    "Translation services — technical documentation",
    "Catering services — corporate meeting, 20 persons",
)

_TIME_UNITS = {"hrs", "hours", "時間", "시간", "小时", "ชั่วโมง", "Std.", "h", "ساعة", "jam"}
_GENERIC_UNITS = {"pcs", "ea", "un", "pza", "unit", "units", "nos"}

# Description keyword groups -> realistic units (handoff item 5: units must
# match what is being sold, not sampled freely).
_UNIT_GROUPS: dict[str, tuple[str, ...]] = {
    "paper": ("paper", "papier", "papel", "kertas", "ream", "resma", "a4",
              "กระดาษ", "ورق", "紙"),
    "services": ("maintenance", "support", "consult", "service", "accounting",
                 "translation", "catering", "wartung", "beratung", "steuerberatung",
                 "übersetzung", "mantenimiento", "soporte", "contabl", "traducc",
                 "serviço", "serviços", "tradução", "manutenção", "perawatan",
                 "jasa", "akuntansi", "terjemahan", "บริการ", "บัญชี", "งานแปล",
                 "จัดเลี้ยง", "صيانة", "خدمات", "محاسب", "ترجمة", "保守", "翻訳",
                 "ケータリング", "유지보수", "번역", "회계", "服务", "咨询", "翻译", "托管"),
    "freight": ("freight", "transport", "shipping", "cargo", "spedition", "fracht",
                "flete", "envío", "frete", "pengiriman", "kirim", "ขนส่ง", "شحن",
                "輸送", "貨物", "운송", "货运", "运输", "物流"),
    "packaging": ("packaging", "corrugated", "carton", "verpackung", "empaque",
                  "embalagem", "kemasan", "包装", "段ボール", "포장", "บรรจุภัณฑ์",
                  "تغليف", "กล่อง"),
}
_GROUP_PREFERRED_UNITS: dict[str, tuple[str, ...]] = {
    "paper": ("ream", "reams", "rim", "carton", "cartons", "box", "boxes", "cx", "dus"),
    "services": ("hrs", "hours", "Std.", "h", "mo", "jam", "ชั่วโมง", "ساعة", "時間",
                 "시간", "小时", "Pauschale", "flat"),
    "freight": ("pallets", "pallet", "tarima", "منصة", "พาเลท", "托"),
    "packaging": ("carton", "cartons", "box", "boxes", "cx", "dus", "pza", "un", "pcs"),
}


@dataclass
class CountrySpec:
    code: str
    name: str                                  # English country name
    currency: str
    native_lang: str                           # ISO 639-1 of the native language
    scripts: tuple[str, ...]                   # ISO 15924 codes (native docs)
    font_stack: tuple[str, ...]                # CSS families, primary first
    direction: str = "ltr"
    page_size: str = "A4"
    number_style: str = "western"
    digit_style: str = "western"
    calendar: str = "gregorian"
    tax_label: str = "Tax"
    vendors: tuple[str, ...] = ()
    vendors_english: tuple[str, ...] = ()
    vendors_fisica: tuple[str, ...] = ()       # person-name vendors (MX retention docs)
    customers: tuple[str, ...] = ()
    vendor_addresses: tuple[tuple[str, ...], ...] = ()
    customer_addresses: tuple[tuple[str, ...], ...] = ()
    customer_tax_label: str = "Tax ID"
    customer_tax_ids: tuple[str, ...] = ()
    descriptions: tuple[str, ...] = ()
    descriptions_english: tuple[str, ...] = ()
    units: tuple[tuple[str, str], ...] = (("pcs", "pcs"),)
    price_range: tuple[int, int] = (10, 1000)  # unit price bounds, currency units
    price_step: int = 1                        # realistic unit-price granularity
    big_price_range: tuple[int, int] | None = None
    labels: dict = field(default_factory=dict)  # native labels (keys of ENGLISH_LABELS)
    tax_id_label_en: str = "Tax ID"
    title_en: str = "INVOICE"
    terms_native: str = "Payment within {days} days"
    terms_en: str = "Payment within {days} days"
    tax_scenarios: dict = field(default_factory=dict)
    doc_plan: tuple[dict, ...] = ()
    tax_id_gen: Callable | None = None         # (rng, name) -> (display, normalized)
    structural_tax_id: Callable | None = None  # name -> (display, normalized), #20
    invoice_no_gen: Callable | None = None     # (rng, date) -> str
    date_render: Callable | None = None        # (date, lang_mode, digits) -> str
    iban_spec: tuple[str, int] | None = None   # (country code, BBAN length)
    bank_lines_gen: Callable | None = None     # rng -> [display-only bank lines]
    use_clabe: bool = False
    reverse_charge_note: str | None = None
    tax_inclusive_note: str | None = None
    amount_words: str | None = None            # "rupees" | "cn_upper" | None
    qr: bool = False
    numeric_dates: bool = False                # day/month rendered numerically (#6)
    integral_amounts: bool = False             # whole-unit amounts (IDR practice, #4)

    def items_pool(self, lang_mode: str) -> tuple[str, ...]:
        if lang_mode == "english":
            return self.descriptions_english or FALLBACK_ENGLISH_ITEMS
        if lang_mode == "bilingual" and self.descriptions_english:
            return self.descriptions + self.descriptions_english
        return self.descriptions

    def unit_pair(self, rng: random.Random, lang_mode: str) -> tuple[str, str]:
        native, english = rng.choice(self.units)
        return (english, native) if lang_mode == "english" else (native, english)


class MoneyDisplay:
    """Pre-renders money exactly as printed (spec B2.5 rendered_strings)."""

    def __init__(self, currency: str, style: str, digits: str, symbol_mode: str):
        self.currency = currency
        self.style = style                        # western | european | indian | space
        self.digits = digits                      # western | arabic_indic
        self.symbol_mode = symbol_mode            # symbol | code | both

    def _fmt(self, value: Decimal) -> str:
        s = money.display_amount(value, self.currency, self.style)
        return money.to_arabic_indic(s) if self.digits == "arabic_indic" else s

    def amount(self, value: Decimal) -> str:
        return self._fmt(value)

    def money(self, value: Decimal) -> str:
        a = self._fmt(value)
        code = self.currency
        suffix_symbol = self.currency in money.SYMBOL_AFTER
        if self.symbol_mode == "code":
            return f"{a} {code}" if suffix_symbol else f"{code} {a}"
        sym = money.SYMBOLS[self.currency]
        core = f"{a} {sym}" if suffix_symbol else f"{sym}{a}"
        return f"{core} ({code})" if self.symbol_mode == "both" else core


def _quant(value: Decimal, currency: str, integral: bool = False) -> Decimal:
    q = value.quantize(Decimal(1).scaleb(-money.MINOR_UNITS[currency]),
                       rounding=ROUND_HALF_UP)
    if integral:                              # whole-unit currencies (IDR practice)
        q = q.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return q


def _fmt_qty(qty: Decimal) -> str:
    return format(qty.normalize(), "f")


def _pick_date(rng: random.Random, ambiguous: bool) -> date:
    year = rng.choice((2025, 2025, 2026, 2026))
    month = rng.randint(1, 12)
    day = rng.randint(1, 12) if ambiguous else rng.randint(1, 28)
    return date(year, month, day)


def _default_date_render(d: date, lang_mode: str, digits: str = "western") -> str:
    s = f"{d.day:02d}/{d.month:02d}/{d.year}"
    return money.to_arabic_indic(s) if digits == "arabic_indic" else s


def _logo_svg(name: str, hue: int) -> str:
    initial = next((ch for ch in name if ch.isalpha()), name[:1])
    return (f'<svg width="64" height="64" viewBox="0 0 64 64">'
            f'<rect width="64" height="64" rx="12" fill="hsl({hue},48%,38%)"/>'
            f'<text x="32" y="44" font-size="30" text-anchor="middle" fill="#ffffff" '
            f'font-family="Noto Sans">{initial}</text></svg>')


def _qr_data_uri(payload: dict) -> str:
    import qrcode
    data = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode()
    img = qrcode.make(data, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _localize(spec: CountrySpec, lang_mode: str) -> dict:
    if lang_mode == "english":
        out = dict(ENGLISH_LABELS)
        out["title"] = spec.title_en
        out["tax_id_label"] = spec.tax_id_label_en
        return out
    if lang_mode == "bilingual":
        out = {}
        for key, en in ENGLISH_LABELS.items():
            native = spec.labels.get(key, en)
            out[key] = native if native == en else f"{native} / {en}"
        out["tax_id_label"] = spec.labels.get("tax_id_label", spec.tax_id_label_en)
        out["title"] = f"{spec.labels['title']} / {spec.title_en}"
        return out
    out = dict(ENGLISH_LABELS)
    out.update(spec.labels)
    return out


def _generic_unit(spec: CountrySpec, lang_mode: str) -> str:
    """The country's plain piece-unit, for descriptions with no special unit."""
    for native, english in spec.units:
        if english.casefold().rstrip(".") in _GENERIC_UNITS:
            return english if lang_mode == "english" else native
    native, english = spec.units[0]
    return english if lang_mode == "english" else native


def _unit_for(spec: CountrySpec, desc: str, lang_mode: str,
              rng: random.Random) -> str | None:
    """Pick a unit matching what the description sells, if the country has one."""
    d = desc.casefold()
    for group, keys in _UNIT_GROUPS.items():
        if not any(k.casefold() in d for k in keys):
            continue
        preferred = _GROUP_PREFERRED_UNITS[group]
        for native, english in spec.units:
            if english.casefold() in preferred or native.casefold() in preferred:
                return english if lang_mode == "english" else native
        return None
    return None


# --------------------------------------------------------------------------- #
# Tax application
# --------------------------------------------------------------------------- #

def _apply_tax(spec: CountrySpec, rng: random.Random, md: MoneyDisplay, currency: str,
               items: list[dict], scenario: dict) -> tuple[Decimal, Decimal, Decimal, list[TaxLine], list[LineItem]]:
    """Apply a tax scenario. Mutates item dicts; returns (subtotal, tax_total,
    total, tax display lines, LineItems). Withholding is applied by the caller
    (DECISIONS.md #18). See module docstring for the invariants."""
    mode = scenario.get("mode", "exclusive")
    rates: list[Decimal] = scenario.get("rates", [Decimal("0")])
    if scenario.get("pick_one") and len(rates) > 1:
        rates = [rng.choice(rates)]      # e.g. one US state sales-tax rate per document
    mixed = bool(scenario.get("mixed")) and len(rates) > 1
    integral = spec.integral_amounts

    line_items: list[LineItem] = []
    tax_by_rate: dict[str, Decimal] = {}
    rate_order: list[str] = []

    for it in items:
        rate = rng.choice(rates) if mixed else rates[0]
        gross = _quant(it["qty"] * it["price"], currency, integral)
        if mode == "inclusive":
            net = _quant(gross / (Q1 + rate / 100), currency, integral)
            tax = gross - net
            amount = gross
        else:
            net = gross
            tax = _quant(gross * rate / 100, currency, integral)
            amount = net
        it["rate"], it["net"], it["tax"], it["amount"] = rate, net, tax, amount
        rate_str = money.fmt_rate(rate)
        if rate_str not in rate_order:
            rate_order.append(rate_str)
        tax_by_rate[rate_str] = tax_by_rate.get(rate_str, Decimal(0)) + tax
        line_items.append(LineItem(
            description=it["desc"], quantity=_fmt_qty(it["qty"]), unit=it["unit"],
            unit_price=it["price"], unit_price_display=md.amount(it["price"]),
            amount_display=md.amount(amount), amount=amount, tax_rate=rate,
            tax_display=md.amount(tax),
        ))

    if mode == "inclusive":
        # exact by construction: per line, net + tax == gross
        total = sum((li.amount for li in line_items), Decimal(0))
        tax_total = sum(tax_by_rate.values(), Decimal(0))
        subtotal = total - tax_total
    else:
        subtotal = sum((li.amount for li in line_items), Decimal(0))
        tax_total = sum(tax_by_rate.values(), Decimal(0))
        total = subtotal + tax_total

    tax_lines: list[TaxLine] = []
    if mode == "reverse_charge":
        tax_lines.append(TaxLine(label=scenario.get("line_label", f"{spec.tax_label} 0%"),
                                 amount_display=md.amount(Decimal(0)), rate_str="0"))
    elif scenario.get("split"):
        # e.g. Indian CGST + SGST printed as two lines at half the applied rate
        rate_decimal = rates[0]
        for prefix, _rs in scenario["split"]:
            half_rate = money.fmt_rate(rate_decimal / 2)
            amount = _quant(subtotal * rate_decimal / 200, currency, integral)
            tax_lines.append(TaxLine(label=f"{prefix} {half_rate}%",
                                     amount_display=md.amount(amount), rate_str=half_rate))
    else:
        labels_map: dict[str, str] = scenario.get("labels", {})
        for rate_str in rate_order:
            label = labels_map.get(rate_str, spec.tax_label)
            tax_lines.append(TaxLine(label=f"{label} {rate_str}%",
                                     amount_display=md.amount(tax_by_rate[rate_str]),
                                     rate_str=rate_str))

    for label, rate in scenario.get("extra_lines", ()):  # e.g. Brazilian PIS/COFINS
        amount = _quant(subtotal * rate / 100, currency, integral)
        tax_total += amount
        total += amount
        tax_lines.append(TaxLine(label=f"{label} {money.fmt_rate(rate)}%",
                                 amount_display=md.amount(amount),
                                 rate_str=money.fmt_rate(rate)))

    return subtotal, tax_total, total, tax_lines, line_items


# --------------------------------------------------------------------------- #
# Invoice assembly
# --------------------------------------------------------------------------- #

def build_invoice(spec: CountrySpec, rng: random.Random, doc_id: str, plan: dict) -> Invoice:
    lang_mode = plan.get("lang", "native")
    cross_border = bool(plan.get("cross_border"))
    currency = plan.get("currency", spec.currency)

    language = {"native": [spec.native_lang],
                "bilingual": [spec.native_lang, "en"],
                "english": ["en"]}[lang_mode]
    script = {"native": list(spec.scripts),
              "bilingual": sorted({*spec.scripts, "Latn"}),
              "english": ["Latn"]}[lang_mode]

    number_style = plan.get("number_style", spec.number_style)
    digits = plan.get("digits", spec.digit_style)
    symbol_mode = plan.get("symbol_mode", "symbol")
    md = MoneyDisplay(currency, number_style, digits, symbol_mode)

    labels = _localize(spec, lang_mode)

    # --- parties (vendor identity: name and tax ID form one stable pair, #20) --
    if plan.get("fisica") and spec.vendors_fisica:
        vendor_name = rng.choice(spec.vendors_fisica)
        canonical_vendor = vendor_name
    else:
        pool = spec.vendors_english if (lang_mode == "english" and spec.vendors_english) \
            else spec.vendors
        vi = rng.randrange(len(pool))
        vendor_name = pool[vi]
        canonical_vendor = spec.vendors[vi] if vi < len(spec.vendors) else vendor_name
    vendor_address = list(rng.choice(spec.vendor_addresses))
    tax_id_display, tax_id_normalized = (None, None)
    if spec.structural_tax_id:
        tax_id_display, tax_id_normalized = spec.structural_tax_id(canonical_vendor)
    elif spec.tax_id_gen:
        tax_id_display, tax_id_normalized = spec.tax_id_gen(rng, canonical_vendor)

    if cross_border:
        ci = rng.randrange(len(FOREIGN_CUSTOMERS))
        customer_name = FOREIGN_CUSTOMERS[ci]
        customer_address = list(FOREIGN_ADDRESSES[ci % len(FOREIGN_ADDRESSES)])
        customer_tax_id_display = None
    else:
        customer_name = rng.choice(spec.customers)
        customer_address = list(rng.choice(spec.customer_addresses))
        customer_tax_id_display = rng.choice(spec.customer_tax_ids) if spec.customer_tax_ids else None

    # --- dates (fapiao carries no due date -> null, DECISIONS.md #20) ----------
    invoice_date = _pick_date(rng, bool(plan.get("ambiguous_date")))
    due_days = rng.choice((14, 15, 30, 30, 45, 60))
    due_date = (None if plan.get("template_style") == "fapiao"
                else invoice_date + timedelta(days=due_days))
    date_render = spec.date_render or _default_date_render
    inv_date_display = date_render(invoice_date, lang_mode, digits)
    due_date_display = date_render(due_date, lang_mode, digits) if due_date else None

    # --- items --------------------------------------------------------------
    n_items = rng.randint(18, 25) if plan.get("many_items") else rng.randint(1, 12)
    pool = list(spec.items_pool(lang_mode))
    chosen: list[str] = rng.sample(pool, min(n_items, len(pool)))
    if n_items > len(pool):
        chosen += rng.choices(pool, k=n_items - len(pool))
    if n_items >= 18:  # force wrapping, multi-page realism (B2.3)
        longs = [d for d in pool if len(d) >= 30][:4]
        for i, d in enumerate(longs[:2]):
            chosen[i] = d

    lo, hi = (spec.big_price_range or spec.price_range) if plan.get("big") else spec.price_range
    items: list[dict] = []
    for desc in chosen:
        unit = _unit_for(spec, desc, lang_mode, rng) or _generic_unit(spec, lang_mode)
        base = rng.randrange(lo, hi)
        base -= base % spec.price_step
        price = Decimal(base)
        if (money.MINOR_UNITS[currency] == 2 and not spec.integral_amounts
                and rng.random() < 0.35):
            price += Decimal(rng.randrange(5, 100)) / 100
        qty_int = rng.choice((1, 1, 2, 2, 3, 4, 5, 6, 8, 10, 12, 20))
        qty = Decimal(qty_int)
        if (unit in _TIME_UNITS and not spec.integral_amounts
                and rng.random() < 0.3):
            qty = Decimal(f"{qty_int}.5")
        items.append({"desc": desc, "unit": unit, "qty": qty, "price": price})

    scenario = spec.tax_scenarios[plan["tax"]]
    subtotal, tax_total, total, tax_lines, line_items = _apply_tax(
        spec, rng, md, currency, items, scenario)

    # --- withholding: buyer-side retention, separate from charged tax (#18) ---
    withholding_total = None
    withholding_lines: list[TaxLine] = []
    if scenario.get("withholding") is not None:
        isr_rate = scenario["withholding"]              # e.g. ISR 10%
        charged_rate = scenario["rates"][0]             # e.g. IVA 16%
        isr_amt = _quant(subtotal * isr_rate / 100, currency, spec.integral_amounts)
        iva_ret_amt = _quant(subtotal * charged_rate * 2 / 300, currency,
                             spec.integral_amounts)      # 2/3 of IVA charged
        withholding_total = isr_amt + iva_ret_amt
        total -= withholding_total
        withholding_lines = [
            TaxLine(label=f"ISR retenida ({money.fmt_rate(isr_rate)}%)",
                    amount_display="-" + md.amount(isr_amt), rate_str=None),
            TaxLine(label="IVA retenida (2/3)",
                    amount_display="-" + md.amount(iva_ret_amt), rate_str=None),
        ]

    # --- payment (#19: printed-but-unnormalizable details unscore, absent stays
    #     scored-null) --------------------------------------------------------
    payment_account = None
    account_display = None
    bank_lines: list[str] = []
    printed_payment_details = False
    if plan.get("show_account", True):
        if spec.iban_spec and rng.random() < 0.85:
            cc, bban_len = spec.iban_spec
            payment_account = idgen.make_iban(rng, cc, bban_len)
            account_display = idgen.iban_display(payment_account)
            printed_payment_details = True
        elif spec.use_clabe and rng.random() < 0.7:
            payment_account = idgen.make_clabe(rng)
            account_display = payment_account
            printed_payment_details = True
        elif spec.bank_lines_gen:
            bank_lines = spec.bank_lines_gen(rng)
            printed_payment_details = True
    unscored_fields = (["payment_account"]
                       if printed_payment_details and payment_account is None else [])

    # --- notes / extras -----------------------------------------------------
    notes: list[str] = []
    if scenario.get("mode") == "reverse_charge" and spec.reverse_charge_note:
        notes.append(spec.reverse_charge_note)
    if scenario.get("mode") == "inclusive" and spec.tax_inclusive_note:
        notes.append(spec.tax_inclusive_note)
    dual_currency_line = None
    if plan.get("dual"):
        rate = Decimal(rng.randrange(10400, 12100)) / 10000
        other = "USD" if currency != "USD" else "EUR"
        other_md = MoneyDisplay(other, "western", "western", "symbol")
        converted = _quant(total * rate, other)
        dual_currency_line = f"≈ {other_md.money(converted)}"
        notes.append(f"Exchange rate for reference only: 1 {currency} = {rate:.4f} {other}")

    hue = rng.randrange(0, 360)
    logo = _logo_svg(vendor_name, hue)

    qr_payload = None
    if spec.qr:
        qr_payload = _qr_data_uri({
            "seller": vendor_name, "vat": tax_id_normalized,
            "date": invoice_date.isoformat(),
            "total": money.to_minor_string(total, currency),
            "vat_amt": money.to_minor_string(tax_total, currency),
        })

    # --- totals display -----------------------------------------------------
    subtotal_rows: list[tuple[str, str]] = []
    if scenario.get("mode") != "inclusive":
        subtotal_rows.append((labels["subtotal"], md.money(subtotal)))

    # --- amount in words ----------------------------------------------------
    amount_in_words = None
    words_label = None
    if spec.amount_words == "rupees":
        amount_in_words = words.rupees_in_words(total)
        words_label = labels["amount_in_words"]
    elif spec.amount_words == "cn_upper":
        amount_in_words = words.chinese_upper_amount(total)
        words_label = "价税合计(大写)"

    # --- rendered strings (spec B2.5) ----------------------------------------
    rendered = {
        "invoice_number": spec.invoice_no_gen(rng, invoice_date) if spec.invoice_no_gen
        else f"INV-{invoice_date.year}-{rng.randrange(10000):04d}",
    }
    # Keep the printed invoice number identical to the one stored.
    invoice_number = rendered["invoice_number"]
    rendered["invoice_date"] = inv_date_display
    if due_date_display:
        rendered["due_date"] = due_date_display
    if subtotal_rows:
        rendered["subtotal"] = subtotal_rows[0][1]
    if len(tax_lines) == 1:
        # with split/multiple taxes the sum is never printed as a single number
        rendered["tax_total"] = tax_lines[0].amount_display
    rendered["total"] = md.money(total)

    terms_template = spec.terms_en if lang_mode == "english" else spec.terms_native
    terms = terms_template.format(days=due_days)

    dimensions = {
        "calendar": spec.calendar,
        "number_format": "native" if (number_style == spec.number_style
                                      and digits == spec.digit_style) else "foreign",
        "digits": digits,
        "tax_mode": scenario.get("mode", "exclusive"),
        "cross_border": cross_border,
        "language_mode": lang_mode,
        "template": f"{spec.code.lower()}_{plan.get('layout', 'a')}",
        "withholding": withholding_total is not None,
        # numeric day/month forms with day ≤ 12 and day ≠ month are genuinely
        # ambiguous DD/MM vs MM/DD (handoff item 6)
        "ambiguous_date": (bool(plan.get("ambiguous_date")) and spec.numeric_dates
                           and invoice_date.day != invoice_date.month),
    }

    return Invoice(
        doc_id=doc_id, country=spec.code, language=language, script=script,
        dimensions=dimensions, title=labels["title"], labels=labels,
        vendor=Vendor(name=vendor_name, address_lines=vendor_address,
                      tax_id_label=labels["tax_id_label"],
                      tax_id_display=tax_id_display, tax_id=tax_id_normalized),
        customer_name=customer_name, customer_address_lines=customer_address,
        customer_tax_id_label=spec.customer_tax_label if customer_tax_id_display else None,
        customer_tax_id_display=customer_tax_id_display,
        invoice_number=invoice_number, invoice_date=invoice_date, due_date=due_date,
        currency=currency, tax_mode=scenario.get("mode", "exclusive"),
        subtotal_rows=subtotal_rows, tax_lines=tax_lines,
        total_display=md.money(total), items=line_items,
        subtotal=subtotal, tax_total=tax_total, total=total,
        payment_account=payment_account, payment_terms_display=terms,
        account_display=account_display,
        withholding_total=withholding_total, withholding_lines=withholding_lines,
        unscored_fields=unscored_fields,
        bank_lines=bank_lines, notes=notes, rendered_strings=rendered,
        dual_currency_line=dual_currency_line, amount_in_words=amount_in_words,
        words_label=words_label, qr_payload=qr_payload, logo_svg=logo, logo_hue=hue,
        template_style=plan.get("template_style", "standard"),
        layout=plan.get("layout", "a"), page_size=spec.page_size,
        direction=spec.direction,
        font_stack_css=", ".join(f"'{f}'" for f in spec.font_stack) + ", sans-serif",
    )
