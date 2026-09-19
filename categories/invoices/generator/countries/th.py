"""TH invoices: Thai script, Buddhist calendar year (Gregorian + 543), VAT 7%."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import calendars, ids, money
from ..build import CountrySpec


def _tax_id(rng: random.Random, name: str) -> tuple[str, str]:
    n = ids.random_digits(rng, 13)
    return f"เลขผู้เสียภาษี {n}", n


def _invoice_no(rng: random.Random, d: date) -> str:
    # Thai invoice numbers often carry the Buddhist year
    return f"INV-{calendars.to_buddhist_year(d)}-{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    if lang_mode == "english":
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        return f"{d.day:02d} {months[d.month - 1]} {d.year}"
    # abbreviated Thai months on compact docs, full month names otherwise
    return calendars.format_thai_date(d, abbr=d.day <= 12)


def make_scenarios(cfg) -> dict:
    return {"vat7": {"mode": "exclusive", "rates": [Decimal(str(cfg[0]))]}}


SPEC = CountrySpec(
    code="TH", name="Thailand", currency="THB",
    native_lang="th", scripts=("Thai",), font_stack=("Noto Sans Thai", "Noto Sans"),
    tax_label="ภาษีมูลค่าเพิ่ม",
    vendors=(
        "บริษัท สยาม ออฟฟิศ ซัพพลาย จำกัด", "บริษัท กรุงเทพ โลจิสติกส์ จำกัด",
        "บริษัท เชียงใหม่ อิเล็กทรอนิกส์ จำกัด", "บริษัท ภูเก็ต ซอฟต์แวร์ จำกัด",
        "บริษัท อีสาน ฟู้ดส์ จำกัด", "บริษัท ธนบุรี ปริ๊นติ้ง จำกัด",
        "บริษัท พัทยา เทรดดิ้ง จำกัด", "บริษัท สงขลา เพเพอร์ จำกัด",
    ),
    vendors_english=(
        "Siam Office Supply Co., Ltd.", "Bangkok Logistics Co., Ltd.",
        "Chiang Mai Electronics Co., Ltd.", "Phuket Software Co., Ltd.",
        "Isaan Foods Co., Ltd.", "Thonburi Printing Co., Ltd.",
        "Pattaya Trading Co., Ltd.", "Songkhla Paper Co., Ltd.",
    ),
    customers=(
        "บริษัท นนทบุรี อุตสาหกรรม จำกัด", "บริษัท ระยอง พลาสติก จำกัด",
        "บริษัท ขอนแก่น ดิสทริบิวชั่น จำกัด", "บริษัท อยุธยา เมทัล จำกัด",
    ),
    vendor_addresses=(
        ("88/8 ถนนสุขุมวิท แขวงพระโขนง", "กรุงเทพมหานคร 10260"),
        ("145/12 ถนนเจริญกรุง แขวงบางรัก", "กรุงเทพมหานคร 10500"),
        ("2/9 ถนนห้วยแก้ว ต.สันป่าเปา", "เชียงใหม่ 50180"),
    ),
    customer_addresses=(
        ("55/3 ถนนงามวงศ์วาน ต.บางกระสอ", "นนทบุรี 11000"),
        ("19/2 ถนนเพชรบุรี แขวงมักกะสัน", "กรุงเทพมหานคร 10400"),
    ),
    customer_tax_label="เลขประจำตัวผู้เสียภาษี",
    labels={
        "title": "ใบกำกับภาษี", "invoice_no": "เลขที่เอกสาร", "invoice_date": "วันที่",
        "due_date": "กำหนดชำระ", "bill_to": "ลูกค้า", "description": "รายการ",
        "qty": "จำนวน", "unit_price": "ราคาต่อหน่วย", "amount": "จำนวนเงิน",
        "subtotal": "รวมเงิน", "total": "ยอดรวมสุทธิ",
        "payment_terms": "เงื่อนไขการชำระ", "payment_account": "บัญชีธนาคาร",
        "tax_id_label": "เลขผู้เสียภาษี",
    },
    tax_id_label_en="Tax ID",
    title_en="TAX INVOICE",
    terms_native="ชำระภายใน {days} วัน",
    terms_en="Payment within {days} days",
    descriptions=(
        "เก้าอี้สำนักงาน ผ้าตาข่าย",
        "บริการบำรุงรักษาประจำเดือน — เซิร์ฟเวอร์ รวมการดูแลระยะไกล",
        "ขนส่งสินค้า: กรุงเทพ → ภูเก็ต 2 พาเลท",
        "ค่าลิขสิทธิ์ซอฟต์แวร์ — รายปี",
        "กระดาษ A4 70 แกรม (1 ลัง 10 รีม)",
        "บริการบัญชี — รายเดือน",
        "งานแปล — ไทย → อังกฤษ",
        "จัดเลี้ยงสำนักงาน — 20 ท่าน",
        "โต๊ะประชุม 240 ซม. ไม้วอลนัท",
        "วัสดุบรรจุภัณฑ์ — กล่องลูกฟูก (500 ใบ)",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Monthly maintenance — servers, remote monitoring",
        "Freight Bangkok → Phuket, 2 pallets",
        "Software license — annual",
        "Paper A4 70gsm (1 carton, 10 reams)",
        "Accounting services — monthly",
    ),
    units=(("ชิ้น", "pcs"), ("หน่วย", "units"), ("รีม", "reams"),
           ("พาเลท", "pallets"), ("ชั่วโมง", "hours")),
    price_range=(150, 12000),
    price_step=1,
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "vat7", "layout": "a", "lang": "native"},
        {"tax": "vat7", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "vat7", "layout": "a", "lang": "bilingual", "many_items": True},
        {"tax": "vat7", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "vat7", "layout": "a", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
        {"tax": "vat7", "layout": "b", "lang": "native"},
        {"tax": "vat7", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "vat7", "layout": "a", "lang": "bilingual"},
    ),
)
