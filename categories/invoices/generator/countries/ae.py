"""AE invoices: Arabic/English bilingual, VAT 5%, TRN, AED, IBAN."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec


def _tax_id(rng: random.Random) -> tuple[str, str]:
    n = "1" + ids.random_digits(rng, 14)
    return n, n


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"TINV/{d.year}/{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def make_scenarios(cfg) -> dict:
    return {"vat5": {"mode": "exclusive", "rates": [Decimal(str(cfg[0]))]}}


SPEC = CountrySpec(
    code="AE", name="United Arab Emirates", currency="AED",
    native_lang="ar", scripts=("Arab",), font_stack=("Noto Naskh Arabic", "Noto Sans"),
    direction="rtl",
    tax_label="ضريبة القيمة المضافة",
    vendors=(
        "دبي للتجارة العامة ذ.م.م", "الشارقة للمكتبات ذ.م.م", "أبوظبي للتوريدات ش.ذ.م.م",
        "عجمان للطباعة والإعلان ذ.م.م", "رأس الخيمة للتجارة ذ.م.م",
        "الفجيرة للإلكترونيات ذ.م.م", "ال عجمان للخدمات المكتبية", "دائرة الشارقة للخدمات",
    ),
    vendors_english=(
        "Dubai General Trading LLC", "Sharjah Bookhouse LLC", "Abu Dhabi Supplies LLC",
        "Ajman Printing & Advertising LLC", "Ras Al Khaimah Trading LLC",
        "Fujairah Electronics LLC", "Al Ajman Office Services", "Sharjah Services Dept.",
    ),
    customers=(
        "النعيمي للاستشارات ذ.م.م", "شركة الخليج الأزرق ذ.م.م", "مجموعة الواحة التجارية",
    ),
    vendor_addresses=(
        ("Sheikh Zayed Road, Al Quoz 3", "Dubai, UAE"),
        ("King Faisal Street", "Sharjah, UAE"),
        ("Hamdan Street, P.O. Box 4488", "Abu Dhabi, UAE"),
    ),
    customer_addresses=(
        ("Al Nahda 2, P.O. Box 55432", "Dubai, UAE"),
        ("Industrial Area 12", "Sharjah, UAE"),
    ),
    customer_tax_label="TRN",
    labels={
        "title": "فاتورة ضريبية", "invoice_no": "رقم الفاتورة",
        "invoice_date": "تاريخ الفاتورة", "due_date": "تاريخ الاستحقاق",
        "bill_to": "العميل", "description": "الوصف", "qty": "الكمية",
        "unit_price": "سعر الوحدة", "amount": "المبلغ",
        "subtotal": "المجموع الفرعي", "total": "الإجمالي",
        "payment_terms": "شروط الدفع", "payment_account": "رقم الآيبان (IBAN)",
        "tax_id_label": "الرقم الضريبي (TRN)",
    },
    tax_id_label_en="TRN",
    title_en="TAX INVOICE",
    terms_native="الدفع خلال {days} يوماً",
    terms_en="Payment within {days} days",
    descriptions=(
        "Office chairs, mesh, ergonomic / كراسي مكتبية",
        "Monthly IT maintenance — servers and network / صيانة شهرية للخوادم",
        "Freight Jebel Ali → Abu Dhabi, 2 pallets / شحن جبل علي → أبوظبي",
        "Software license — annual / ترخيص برمجيات سنوي",
        "Paper A4, carton of 10 reams / ورق A4 (كرتون)",
        "Accounting services — monthly / خدمات محاسبية شهرية",
        "Office desks, 160 cm, walnut / مكاتب خشبية",
        "Translation AR → EN / ترجمة عربي → إنجليزي",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Monthly IT maintenance — servers and network",
        "Freight Jebel Ali → Abu Dhabi, 2 pallets",
        "Software license — annual",
        "Paper A4, carton of 10 reams",
        "Accounting services — monthly",
    ),
    units=(("pcs", "pcs"), ("hrs", "hrs"), ("carton", "cartons"), ("pallet", "pallets")),
    price_range=(20, 3000),
    price_step=1,
    iban_spec=("AE", 19),
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "vat5", "layout": "a", "lang": "bilingual"},
        {"tax": "vat5", "layout": "b", "lang": "bilingual", "symbol_mode": "both"},
        {"tax": "vat5", "layout": "a", "lang": "bilingual", "many_items": True},
        {"tax": "vat5", "layout": "c", "lang": "bilingual", "ambiguous_date": True},
        {"tax": "vat5", "layout": "a", "lang": "english"},
        {"tax": "vat5", "layout": "b", "lang": "bilingual"},
        {"tax": "vat5", "layout": "c", "lang": "bilingual", "ambiguous_date": True},
        {"tax": "vat5", "layout": "a", "lang": "bilingual"},
    ),
)
