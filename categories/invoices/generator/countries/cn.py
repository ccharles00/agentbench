"""CN invoices: Chinese script, simplified fapiao style, ¥ ambiguity (CNY),
18-char unified social credit code with a real mod-31 check character (#20)."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec


def _structural_uscc(name: str) -> tuple[str, str]:
    """USCC per GB 32100-2015, stable per vendor name.

    char 0: registration authority (1/5/9/Y); char 1: entity type; chars 2-7:
    6-digit division code; chars 8-16: organization code; char 17: mod-31 check.
    """
    rng = ids.stable_rng("USCC:" + name)
    body = (rng.choice("159")
            + rng.choice(ids.USCC_ALPHABET)
            + "".join(rng.choice("0123456789") for _ in range(6))
            + "".join(rng.choice(ids.USCC_ALPHABET) for _ in range(9)))
    code = body + ids.uscc_check_char(body)
    return code, code


def _invoice_no(rng: random.Random, d: date) -> str:
    if rng.random() < 0.5:
        return f"{rng.randrange(10**7, 10**8)}"          # fapiao 8-digit number
    return f"INV{d.year}{d.month:02d}{rng.randrange(1, 1000):03d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    if lang_mode == "english":
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        return f"{d.day:02d} {months[d.month - 1]} {d.year}"
    return f"{d.year}年{d.month}月{d.day}日"


def make_scenarios(cfg) -> dict:
    goods = Decimal(str(cfg[0]))
    transport = Decimal(str(cfg[1]))
    services = Decimal(str(cfg[2]))
    return {
        "goods13": {"mode": "exclusive", "rates": [goods]},
        "transport9": {"mode": "exclusive", "rates": [transport]},
        "services6": {"mode": "exclusive", "rates": [services]},
        "mixed": {"mode": "exclusive", "rates": [goods, services], "mixed": True,
                  "labels": {money_fmt(goods): "税额", money_fmt(services): "税额"}},
    }


def money_fmt(r: Decimal) -> str:
    from .. import money
    return money.fmt_rate(r)


SPEC = CountrySpec(
    code="CN", name="China", currency="CNY",
    native_lang="zh", scripts=("Hani",), font_stack=("Noto Sans SC", "Noto Sans"),
    tax_label="税额",
    vendors=(
        "深圳市华信电子有限公司", "上海东方贸易有限公司", "北京中科软件股份有限公司",
        "广州顺达物流有限公司", "杭州西湖印务有限公司", "成都锦程会计师事务所",
        "青岛海润食品有限公司", "义乌市小商品进出口有限公司",
    ),
    vendors_english=(
        "Shenzhen Huaxin Electronics Co., Ltd.", "Shanghai Eastern Trading Co., Ltd.",
        "Beijing Zhongke Software Co., Ltd.", "Guangzhou Shunda Logistics Co., Ltd.",
        "Hangzhou Xihu Printing Co., Ltd.", "Chengdu Jincheng CPA Co., Ltd.",
        "Qingdao Hairun Foods Co., Ltd.", "Yiwu Import & Export Co., Ltd.",
    ),
    customers=(
        "南京长江制造有限公司", "武汉光谷科技有限公司", "西安泰达贸易有限公司",
        "苏州工业园区精密机械有限公司", "厦门海西电子商务有限公司",
    ),
    vendor_addresses=(
        ("南山区科技园南路 15 号", "深圳市 518057"),
        ("浦东新区世纪大道 100 号", "上海市 200120"),
        ("海淀区中关村大街 27 号", "北京市 100080"),
        ("天河区体育西路 8 号", "广州市 510620"),
    ),
    customer_addresses=(
        ("江宁开发区天元东路 9 号", "南京市 211100"),
        ("光谷大道 77 号", "武汉市 430074"),
        ("高新区科技路 33 号", "西安市 710075"),
    ),
    customer_tax_label="纳税人识别号",
    labels={
        "title": "发 票", "invoice_no": "发票号码", "invoice_date": "开票日期",
        "due_date": "付款期限", "bill_to": "购买方", "description": "项目名称",
        "qty": "数量", "unit_price": "单价", "amount": "金额",
        "subtotal": "合计", "total": "价税合计",
        "payment_terms": "付款条件", "tax_id_label": "纳税人识别号",
    },
    tax_id_label_en="Tax ID",
    title_en="INVOICE",
    terms_native="付款条件：{days}日内",
    terms_en="Payment within {days} days",
    descriptions=(
        "办公椅，网布，人体工学",
        "服务器托管服务 — 一年，含带宽与运维值守",
        "电子元器件 — 电阻 10kΩ ±1%（1000 个/盘）",
        "货运：深圳 → 上海，2 托，汽运",
        "财务咨询服务 — 月度报表及税务申报",
        "印刷品：产品手册，500 册，铜版纸",
        "月饼礼盒装（食品，含税）",
        "软件许可 — 年度订阅，20 用户",
        "会议桌，1.8 米，胡桃木色",
        "翻译服务 — 中文译英文，技术文档 40 页",
        "LED 显示屏模组 P2.5，含控制系统",
        "包装材料 — 瓦楞纸箱 5 号（1000 只）",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Server hosting service — one year, bandwidth included",
        "Electronic components — resistors 10kΩ (1000 pcs/reel)",
        "Freight: Shenzhen → Shanghai, 2 pallets",
        "Financial consulting — monthly reporting",
        "Software license — annual subscription, 20 users",
        "LED display module P2.5, with control system",
        "Packaging materials — corrugated cartons (1000 pcs)",
    ),
    units=(("个", "pcs"), ("件", "pcs"), ("托", "pallets"), ("小时", "hours"), ("册", "copies")),
    price_range=(25, 6000),
    price_step=1,
    structural_tax_id=_structural_uscc,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "goods13", "layout": "c", "lang": "native", "template_style": "fapiao"},
        {"tax": "goods13", "layout": "a", "lang": "native", "symbol_mode": "both"},
        {"tax": "services6", "layout": "c", "lang": "native", "template_style": "fapiao"},
        {"tax": "transport9", "layout": "b", "lang": "native", "ambiguous_date": True},
        {"tax": "goods13", "layout": "a", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
        {"tax": "goods13", "layout": "c", "lang": "native", "template_style": "fapiao"},
        {"tax": "mixed", "layout": "b", "lang": "native", "many_items": True},
        {"tax": "services6", "layout": "a", "lang": "bilingual"},
    ),
)
