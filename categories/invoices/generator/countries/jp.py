"""JP invoices: Japanese script, ¥ (JPY, zero decimals), Reiwa era dates,
consumption tax 10%/8%, invoice registration number."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import calendars, ids
from ..build import CountrySpec


def _tax_id(rng: random.Random, name: str) -> tuple[str, str]:
    t = "T" + ids.random_digits(rng, 13)
    return t, t


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"INV-{d.year}-{rng.randrange(1, 100000):05d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    if lang_mode == "english":
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        return f"{months[d.month - 1]} {d.day}, {d.year}"
    return calendars.format_japanese_date(d)


def _bank_lines(rng: random.Random) -> list[str]:
    banks = ("三菱UFJ銀行", "みずほ銀行", "三井住友銀行", "りそな銀行")
    branches = ("本店", "東京営業部", "大阪支店", "名古屋支店")
    return [f"お振込先：{rng.choice(banks)} {rng.choice(branches)} （普通）{ids.random_digits(rng, 7)}"]


def make_scenarios(cfg) -> dict:
    std = Decimal(str(cfg[0]))    # 10
    reduced = Decimal(str(cfg[1]))  # 8
    return {
        "std10": {"mode": "exclusive", "rates": [std]},
        "food8": {"mode": "exclusive", "rates": [reduced]},
        "mixed": {"mode": "exclusive", "rates": [std, reduced], "mixed": True,
                  "labels": {money_fmt(std): "消費税",
                             money_fmt(reduced): "消費税（軽減）"}},
        "std10_incl": {"mode": "inclusive", "rates": [std]},
        "food8_incl": {"mode": "inclusive", "rates": [reduced]},
    }


def money_fmt(r: Decimal) -> str:
    from .. import money
    return money.fmt_rate(r)


SPEC = CountrySpec(
    code="JP", name="Japan", currency="JPY",
    native_lang="ja", scripts=("Jpan",), font_stack=("Noto Sans JP", "Noto Sans"),
    calendar="japanese_era",
    tax_label="消費税",
    vendors=(
        "東京オフィスサプライ株式会社", "大阪物流株式会社", "名古屋電機株式会社",
        "福岡ソフトウェア株式会社", "札幌フーズ株式会社", "横浜貿易株式会社",
        "京都デザイン事務所", "広島機工株式会社",
    ),
    vendors_english=(
        "Tokyo Office Supply K.K.", "Osaka Logistics K.K.", "Nagoya Denki K.K.",
        "Fukuoka Software K.K.", "Sapporo Foods K.K.", "Yokohama Trading K.K.",
        "Kyoto Design Office", "Hiroshima Kiko K.K.",
    ),
    customers=(
        "川崎製造株式会社", "仙台商事株式会社", "広島運輸株式会社",
        "岡山精密工業株式会社", "静岡電子株式会社",
    ),
    vendor_addresses=(
        ("東京都千代田区丸の内 2-7-2", "JP Tower 12F"),
        ("大阪市北区梅田 3-3-1", "アクティ大阪 18F"),
        ("名古屋市中村区名駅 4-2-28", "名古屋第三ビル 5F"),
        ("福岡市博多区博多駅前 2-11-7", "博多ビジネスセンター 601"),
    ),
    customer_addresses=(
        ("川崎市幸区大幸町 2-11", "212-0031 神奈川県"),
        ("仙台市青葉区中央 1-3-1", "980-0021 宮城県"),
        ("岡山市北区駅元町 14-1", "700-0024 岡山県"),
    ),
    customer_tax_label="登録番号",
    labels={
        "title": "請求書", "invoice_no": "請求書番号", "invoice_date": "請求日",
        "due_date": "支払期限", "bill_to": "請求先", "description": "品目",
        "qty": "数量", "unit_price": "単価", "amount": "金額",
        "subtotal": "小計", "total": "合計（税込）",
        "payment_terms": "支払条件", "payment_account": "振込口座",
        "tax_id_label": "登録番号",
    },
    tax_id_label_en="Registration No.",
    title_en="INVOICE",
    terms_native="{days}日以内にお支払いください",
    terms_en="Payment within {days} days",
    tax_inclusive_note="※ 上記価格は消費税（内税）込みです。",
    descriptions=(
        "オフィスチェア（メッシュ、アーム付き）",
        "月額保守サポート — サーバー 3 台、リモート監視込み",
        "貨物輸送 大阪 → 東京、2 パレット",
        "ソフトウェアライセンス（年間）",
        "消耗品：トナーカートリッジ 黒",
        "ケータリング — 役員会議 20 名",
        "書籍：会計実務の手引き（軽減税率対象）",
        "翻訳サービス 日本語 → 英語",
        "ネットワーク機器 24 ポートスイッチ",
        "清掃サービス — オフィス月次",
        "包装資材 — 段ボール 60 サイズ（100 枚）",
        "事務用品一式（文房具、ファイル等）",
    ),
    descriptions_english=(
        "Office chairs, mesh, with arms",
        "Monthly maintenance — 3 servers, remote monitoring",
        "Freight Osaka → Tokyo, 2 pallets",
        "Software license (annual)",
        "Office supplies — stationery and files",
        "Cleaning service — office, monthly",
    ),
    units=(("台", "units"), ("個", "pcs"), ("式", "lots"), ("冊", "copies"), ("時間", "hours")),
    price_range=(300, 90000),
    price_step=100,
    bank_lines_gen=_bank_lines,
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "std10", "layout": "a", "lang": "native"},
        {"tax": "std10", "layout": "b", "lang": "native", "symbol_mode": "both",
         "show_account": False},
        {"tax": "food8", "layout": "a", "lang": "bilingual"},
        {"tax": "std10_incl", "layout": "b", "lang": "native", "ambiguous_date": True},
        {"tax": "std10", "layout": "a", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
        {"tax": "mixed", "layout": "b", "lang": "native", "many_items": True,
         "show_account": False},
        {"tax": "food8_incl", "layout": "a", "lang": "native", "ambiguous_date": True},
        {"tax": "std10", "layout": "c", "lang": "native"},
    ),
)
