"""IN invoices: lakh/crore grouping (1,00,000), CGST+SGST vs IGST, GSTIN,
Devanagari + English mixing."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids, words
from ..build import CountrySpec

_GSTIN_STATES = ("27", "07", "29", "33", "24", "06", "19", "08")
_GSTIN_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def _gstin(rng: random.Random) -> str:
    pan = ("".join(rng.choice(_GSTIN_LETTERS) for _ in range(5))
           + ids.random_digits(rng, 4) + rng.choice(_GSTIN_LETTERS))
    return (rng.choice(_GSTIN_STATES) + pan + rng.choice("123456789") + "Z"
            + rng.choice(_GSTIN_LETTERS))


def _tax_id(rng: random.Random) -> tuple[str, str]:
    g = _gstin(rng)
    return f"GSTIN: {g}", g


def _invoice_no(rng: random.Random, d: date) -> str:
    fy = f"{str(d.year)[2:]}/{str(d.year + 1)[2:]}" if d.month > 3 else \
        f"{str(d.year - 1)[2:]}/{str(d.year)[2:]}"
    return f"{rng.choice(('INV', 'GST', 'TAX'))}/{fy}/{rng.randrange(1, 1000):03d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def make_scenarios(cfg) -> dict:
    # cfg: GST slabs [5, 12, 18, 28]
    slabs = [Decimal(str(r)) for r in cfg]
    scenarios = {}
    for r in slabs:
        s = money_fmt(r)
        scenarios[f"igst{s}"] = {"mode": "exclusive", "rates": [r]}
        scenarios[f"split{s}"] = {"mode": "exclusive", "rates": [r],
                                  "split": (("CGST", s), ("SGST", s))}
    return scenarios


def money_fmt(r: Decimal) -> str:
    from .. import money
    return money.fmt_rate(r)


SPEC = CountrySpec(
    code="IN", name="India", currency="INR",
    native_lang="hi", scripts=("Deva",), font_stack=("Noto Sans Devanagari", "Noto Sans"),
    number_style="indian",
    tax_label="GST",
    vendors=(
        "Shree Ganesh Traders Pvt. Ltd.", "दिल्ली ऑफिस सप्लाई प्राइवेट लिमिटेड",
        "Mumbai Freight Systems Pvt. Ltd.", "सूरज इलेक्ट्रॉनिक्स लिमिटेड",
        "Bengaluru Software Services Pvt. Ltd.", "Gujarat Textiles Mills Ltd.",
        "चेन्नई फूड्स प्राइवेट लिमिटेड", "Jaipur Handicrafts Emporium Pvt. Ltd.",
    ),
    vendors_english=(
        "Shree Ganesh Traders Pvt. Ltd.", "Delhi Office Supply Pvt. Ltd.",
        "Mumbai Freight Systems Pvt. Ltd.", "Suraj Electronics Ltd.",
        "Bengaluru Software Services Pvt. Ltd.", "Gujarat Textiles Mills Ltd.",
        "Chennai Foods Pvt. Ltd.", "Jaipur Handicrafts Emporium Pvt. Ltd.",
    ),
    customers=(
        "Pune Manufacturing Pvt. Ltd.", "हैदराबाद ट्रेडर्स प्राइवेट लिमिटेड",
        "Kolkata Distribution Co.", "अहमदाबाद पैकेजिंग लिमिटेड", "Noida IT Solutions Pvt. Ltd.",
    ),
    vendor_addresses=(
        ("12, MG Road, Ground Floor", "Bengaluru 560001, Karnataka"),
        ("45, Nehru Place", "New Delhi 110019"),
        ("301, Andheri Business Centre", "Mumbai 400053, Maharashtra"),
        ("78, Anna Salai", "Chennai 600002, Tamil Nadu"),
        ("Plot 9, Sector 62", "Noida 201309, Uttar Pradesh"),
    ),
    customer_addresses=(
        ("22, Baner Road", "Pune 411045, Maharashtra"),
        ("5-1-112, Lakdikapul", "Hyderabad 500004, Telangana"),
        ("14, Park Street", "Kolkata 700016, West Bengal"),
        ("88, SG Highway", "Ahmedabad 380054, Gujarat"),
    ),
    customer_tax_label="GSTIN",
    customer_tax_ids=(),  # filled per doc below
    labels={
        "title": "TAX INVOICE", "invoice_no": "Invoice No.", "invoice_date": "Invoice Date",
        "due_date": "Due Date", "bill_to": "Bill To", "description": "Description of Goods / Services",
        "qty": "Qty", "unit_price": "Rate", "amount": "Amount",
        "subtotal": "Taxable Value", "total": "Grand Total",
        "payment_terms": "Payment Terms", "tax_id_label": "GSTIN",
    },
    tax_id_label_en="GSTIN",
    title_en="TAX INVOICE",
    terms_native="Payment within {days} days",
    reverse_charge_note=None,
    descriptions=(
        "ऑफिस कुर्सी, जाली, एर्गोनोमिक",
        "Monthly IT AMC — 40 workstations, on-site support every week",
        "GST registration and compliance consultancy",
        "Bulk notebook supply — A4, 200 pages (pack of 50)",
        "Freight: Mumbai → Delhi, 3 pallets, FTL",
        "LED bulbs 9W (box of 100)",
        "Software subscription — annual, cloud hosted",
        "Handicraft export packing and documentation services",
        "Catering staff — corporate event, 50 guests",
        "Network switches — 24 port, gigabit (5 units)",
        "कपड़ा ढेर: सूती कपड़े, 500 मीटर",
        "मसाला पैकेजिंग सेवा — 2 टन",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "IT annual maintenance — 40 workstations",
        "Freight: Mumbai → Delhi, 3 pallets",
        "Software subscription — annual, cloud hosted",
        "LED bulbs 9W (box of 100)",
        "Export packing and documentation services",
    ),
    units=(("pcs", "pcs"), ("Nos.", "Nos."), ("hrs", "hrs"), ("Box", "Box"), ("kg", "kg")),
    price_range=(50, 25000),
    price_step=10,
    big_price_range=(50000, 250000),
    amount_words="rupees",
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "igst18", "layout": "a", "lang": "native", "big": True},
        {"tax": "split18", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "igst12", "layout": "a", "lang": "bilingual"},
        {"tax": "igst28", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "split18", "layout": "a", "lang": "bilingual", "big": True, "many_items": True},
        {"tax": "igst5", "layout": "b", "lang": "native"},
        {"tax": "split12", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "igst18", "layout": "b", "lang": "english", "cross_border": True,
         "symbol_mode": "code"},
    ),
)
