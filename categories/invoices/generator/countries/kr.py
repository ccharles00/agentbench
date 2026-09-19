"""KR invoices: Korean script, KRW zero decimals, VAT 10%."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec


def _tax_id(rng: random.Random) -> tuple[str, str]:
    body = f"{ids.random_digits(rng, 3)}-{ids.random_digits(rng, 2)}-{ids.random_digits(rng, 5)}"
    return body, body.replace("-", "")


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"{d.year}-{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    if lang_mode == "english":
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        return f"{months[d.month - 1]} {d.day}, {d.year}"
    return f"{d.year}. {d.month:02d}. {d.day:02d}."


def make_scenarios(cfg) -> dict:
    return {"vat10": {"mode": "exclusive", "rates": [Decimal(str(cfg[0]))]}}


SPEC = CountrySpec(
    code="KR", name="South Korea", currency="KRW",
    native_lang="ko", scripts=("Hang",), font_stack=("Noto Sans KR", "Noto Sans"),
    tax_label="부가세",
    vendors=(
        "한빛테크 주식회사", "서울오피스 주식회사", "부산물류 주식회사",
        "대전전자 주식회사", "인천소프트 주식회사", "광주식품 주식회사",
        "제주무역 주식회사", "수원디자인 주식회사",
    ),
    vendors_english=(
        "Hanbit Tech Co., Ltd.", "Seoul Office Co., Ltd.", "Busan Logistics Co., Ltd.",
        "Daejeon Electronics Co., Ltd.", "Incheon Soft Co., Ltd.", "Gwangju Foods Co., Ltd.",
        "Jeju Trading Co., Ltd.", "Suwon Design Co., Ltd.",
    ),
    customers=(
        "성남제조 주식회사", "울산산업 주식회사", "광명상사 주식회사",
        "안양유통 주식회사", "천안전자 주식회사",
    ),
    vendor_addresses=(
        ("서울특별시 강남구 테헤란로 123", "4층"),
        ("부산광역시 해운대구 센텀중앙로 78", "9층"),
        ("대전광역시 유성구 대학로 45", "2호관 301호"),
        ("인천광역시 연수구 송도과학로 16-1", "동관 502호"),
    ),
    customer_addresses=(
        ("경기도 성남시 분당구 판교로 228", "15층"),
        ("울산광역시 남구 삼산로 100", "3층"),
        ("경기도 안양시 동안구 시민대로 180", "7층"),
    ),
    customer_tax_label="사업자등록번호",
    labels={
        "title": "청구서", "invoice_no": "청구서 번호", "invoice_date": "발행일",
        "due_date": "지급기한", "bill_to": "공급받는자", "description": "품목",
        "qty": "수량", "unit_price": "단가", "amount": "금액",
        "subtotal": "공급가액", "total": "합계",
        "payment_terms": "지급조건", "payment_account": "계좌번호",
        "tax_id_label": "사업자등록번호",
    },
    tax_id_label_en="Business Reg. No.",
    title_en="INVOICE",
    terms_native="{days}일 이내 지불",
    terms_en="Payment within {days} days",
    descriptions=(
        "오피스 체어 (메시, 인체공학)",
        "서버 유지보수 — 월간, 원격 모니터링 포함",
        "화물 운송: 부산 → 서울, 2팔레트",
        "소프트웨어 라이선스 — 연간",
        "소모품: 토너 카트리지 (흑색)",
        "케이터링 — 임원 회의 20명",
        "번역 서비스 — 한국어→영어",
        "네트워크 스위치 24포트",
        "사무용품 일괄 (문구, 파일 등)",
        "포장재 — 골판지 박스 (100매)",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Server maintenance — monthly, remote monitoring",
        "Freight Busan → Seoul, 2 pallets",
        "Software license — annual",
        "Office supplies — stationery and files",
        "Catering — executive meeting, 20 persons",
    ),
    units=(("개", "pcs"), ("대", "units"), ("식", "lots"), ("시간", "hours")),
    price_range=(5000, 900000),
    price_step=100,
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "vat10", "layout": "a", "lang": "native"},
        {"tax": "vat10", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "vat10", "layout": "a", "lang": "bilingual"},
        {"tax": "vat10", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "vat10", "layout": "a", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
        {"tax": "vat10", "layout": "b", "lang": "native", "many_items": True},
        {"tax": "vat10", "layout": "c", "lang": "native"},
        {"tax": "vat10", "layout": "a", "lang": "native", "ambiguous_date": True},
    ),
)
