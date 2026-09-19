"""ID invoices: Indonesian, period or space thousands, PPN VAT, IDR large
amounts (displayed whole, canonical at ISO 2 minor units — see DECISIONS.md)."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec

_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")


def _tax_id(rng: random.Random, name: str) -> tuple[str, str]:
    body = (f"{ids.random_digits(rng, 2)}.{ids.random_digits(rng, 3)}."
            f"{ids.random_digits(rng, 3)}.{ids.random_digits(rng, 1)}-"
            f"{ids.random_digits(rng, 3)}.{ids.random_digits(rng, 3)}")
    return body, body.replace(".", "").replace("-", "")


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"INV/{d.year}/{_ROMAN[d.month - 1]}/{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def make_scenarios(cfg) -> dict:
    return {"ppn11": {"mode": "exclusive", "rates": [Decimal(str(cfg[0]))]}}


SPEC = CountrySpec(
    code="ID", name="Indonesia", currency="IDR",
    native_lang="id", scripts=("Latn",), font_stack=("Noto Sans",),
    number_style="european",
    numeric_dates=True,
    integral_amounts=True,   # Indonesian practice: whole rupiah (DECISIONS #3 fix)
    tax_label="PPN",
    vendors=(
        "PT Nusantara Elektronik", "PT Surya Kencana Logistik", "PT Jaya Abadi Komputer",
        "PT Borneo Paperindo", "PT Cahaya Timur Konsultan", "PT Maju Bersama Printindo",
        "PT Sumatera Agro Food", "PT Karya Digital Indonesia",
    ),
    customers=(
        "PT Semarang Manufaktur", "PT Bandung Distribusi", "PT Medan Karya Perkasa",
        "PT Makmur Sentosa", "PT Bali Anugerah Niaga",
    ),
    vendor_addresses=(
        ("Jl. Jenderal Sudirman Kav. 52-53, SCBD", "Jakarta Selatan 12190"),
        ("Jl. Gatot Subroto Km. 3,4", "Medan 20123"),
        ("Jl. Asia Afrika No. 8", "Bandung 40111"),
        ("Jl. Pemuda No. 27", "Semarang 50132"),
    ),
    customer_addresses=(
        ("Jl. Diponegoro No. 14", "Surabaya 60241"),
        ("Jl. Ahmad Yani No. 99", "Palembang 30126"),
        ("Jl. Sunset Road No. 5", "Kuta, Bali 80361"),
    ),
    customer_tax_label="NPWP",
    labels={
        "title": "FAKTUR", "invoice_no": "No. Faktur", "invoice_date": "Tanggal",
        "due_date": "Jatuh Tempo", "bill_to": "Kepada", "description": "Deskripsi",
        "qty": "Qty", "unit_price": "Harga Satuan", "amount": "Jumlah",
        "subtotal": "Subtotal", "total": "Total",
        "payment_terms": "Syarat Pembayaran", "payment_account": "Rekening",
        "tax_id_label": "NPWP",
    },
    tax_id_label_en="Tax ID (NPWP)",
    title_en="INVOICE",
    terms_native="Pembayaran dalam {days} hari",
    terms_en="Payment within {days} days",
    descriptions=(
        "Kursi kantor, jaring, ergonomis",
        "Perawatan bulanan — server dan jaringan, termasuk dukungan jarak jauh",
        "Pengiriman: Jakarta → Surabaya, 2 palet",
        "Lisensi perangkat lunak — tahunan",
        "Kertas A4 70 gram (1 dus isi 10 rim)",
        "Jasa akuntansi — bulanan",
        "Layanan terjemahan — Indonesia → Inggris",
        "Katering kantor — 20 orang",
        "Switch jaringan 24 port",
        "Bahan kemasan — kardus kopling (500 pcs)",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Monthly maintenance — servers and network",
        "Freight Jakarta → Surabaya, 2 pallets",
        "Software license — annual",
        "Paper A4 70gsm (carton of 10 reams)",
        "Accounting services — monthly",
    ),
    units=(("pcs", "pcs"), ("unit", "units"), ("dus", "cartons"), ("rim", "reams"),
           ("jam", "hours")),
    price_range=(25000, 4000000),
    price_step=500,
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "ppn11", "layout": "a", "lang": "native"},
        {"tax": "ppn11", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "ppn11", "layout": "a", "lang": "native", "number_style": "space",
         "many_items": True},
        {"tax": "ppn11", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "ppn11", "layout": "a", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
        {"tax": "ppn11", "layout": "b", "lang": "native", "number_style": "space"},
        {"tax": "ppn11", "layout": "c", "lang": "native"},
        {"tax": "ppn11", "layout": "a", "lang": "bilingual", "ambiguous_date": True},
    ),
)
