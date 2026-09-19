"""SA invoices: Arabic RTL with LTR numbers, Arabic-Indic digit variants,
VAT 15%, ZATCA-style QR code present."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids, money
from ..build import CountrySpec


def _tax_id(rng: random.Random, name: str) -> tuple[str, str]:
    n = "3" + ids.random_digits(rng, 14)
    return n, n


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"INV-{d.year}-{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    s = f"{d.day:02d}/{d.month:02d}/{d.year}"
    return money.to_arabic_indic(s) if digits == "arabic_indic" else s


def make_scenarios(cfg) -> dict:
    return {"vat15": {"mode": "exclusive", "rates": [Decimal(str(cfg[0]))]}}


SPEC = CountrySpec(
    code="SA", name="Saudi Arabia", currency="SAR",
    native_lang="ar", scripts=("Arab",), font_stack=("Noto Naskh Arabic", "Noto Sans"),
    direction="rtl",
    numeric_dates=True,
    tax_label="ضريبة القيمة المضافة",
    vendors=(
        "شركة الرياض للتجارة المحدودة", "مؤسسة جدة للإلكترونيات", "شركة الخليج للمقاولات",
        "شركة الدمام للتوريدات المكتبية", "مؤسسة مكة للتغذية", "شركة المدينة للطباعة",
        "شركة أبها للخدمات المكتبية", "مؤسسة تبوك للتجارة العامة",
    ),
    vendors_english=(
        "Riyadh Trading Co. Ltd.", "Jeddah Electronics Est.", "Gulf Contracting Co.",
        "Dammam Office Supplies Est.", "Makkah Foodstuff Est.", "Madinah Printing Co.",
        "Abha Office Services Co.", "Tabuk General Trading Est.",
    ),
    customers=(
        "شركة الأحساء للصناعات المحدودة", "مؤسسة نجران للتجارة",
        "شركة تبوك للمقاولات", "مؤسسة حائل للتجارة العامة",
    ),
    vendor_addresses=(
        ("طريق الملك فهد، حي العليا", "الرياض 12212"),
        ("شارع التحلية، حي الروضة", "جدة 23435"),
        ("طريق الملك عبدالعزيز، حي السلامة", "الدمام 32417"),
    ),
    customer_addresses=(
        ("المنطقة الصناعية الثانية", "الأحساء 36421"),
        ("شارع الملك عبدالله، حي الندى", "نجران 66211"),
    ),
    customer_tax_label="الرقم الضريبي",
    labels={
        "title": "فاتورة ضريبية", "invoice_no": "رقم الفاتورة",
        "invoice_date": "تاريخ الفاتورة", "due_date": "تاريخ الاستحقاق",
        "bill_to": "العميل", "description": "الوصف", "qty": "الكمية",
        "unit_price": "سعر الوحدة", "amount": "المبلغ",
        "subtotal": "المجموع الفرعي", "total": "الإجمالي",
        "payment_terms": "شروط الدفع", "payment_account": "رقم الآيبان (IBAN)",
        "tax_id_label": "الرقم الضريبي",
    },
    tax_id_label_en="VAT No.",
    title_en="TAX INVOICE",
    terms_native="الدفع خلال {days} يوماً",
    terms_en="Payment within {days} days",
    descriptions=(
        "كرسي مكتبي، شبكي، مريح",
        "صيانة شهرية — خوادم و شبكة، دعم عن بعد مشمول",
        "نقل البضائع: الرياض → جدة، 2 منصات",
        "ترخيص برمجيات — سنوي",
        "ورق A4 (كرتون 10 رزم)",
        "خدمات محاسبية — شهرية",
        "تغذية مكتبية — 20 شخص",
        "ترجمة — عربي → إنجليزي",
        "مكتب خشبي، 180 سم، مع أدراج",
        "مواد تغليف — صناديق كرتون (500 حبة)",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Monthly maintenance — servers and network",
        "Freight Riyadh → Jeddah, 2 pallets",
        "Software license — annual",
        "Paper A4 (carton of 10 reams)",
        "Accounting services — monthly",
    ),
    units=(("حبة", "pcs"), ("ساعة", "hours"), ("كرتون", "cartons"), ("منصة", "pallets")),
    price_range=(25, 3500),
    price_step=1,
    iban_spec=("SA", 22),
    qr=True,
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "vat15", "layout": "a", "lang": "bilingual", "digits": "arabic_indic"},
        {"tax": "vat15", "layout": "b", "lang": "bilingual", "digits": "arabic_indic",
         "symbol_mode": "both"},
        {"tax": "vat15", "layout": "a", "lang": "bilingual", "many_items": True},
        {"tax": "vat15", "layout": "c", "lang": "bilingual", "ambiguous_date": True},
        {"tax": "vat15", "layout": "a", "lang": "bilingual"},
        {"tax": "vat15", "layout": "b", "lang": "bilingual", "digits": "arabic_indic"},
        {"tax": "vat15", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "vat15", "layout": "a", "lang": "bilingual"},
    ),
)
