"""BR invoices: Portuguese, comma decimals, NF-e/DANFE-style layout (simplified),
ICMS by state + PIS/COFINS on some documents, occasional tax-inclusive pricing."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec

_CNPJ_WEIGHTS1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_WEIGHTS2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _cnpj(rng: random.Random) -> tuple[str, str]:
    base = [rng.randrange(10) for _ in range(8)] + [0, 0, 0, 1]
    def check(weights):
        s = sum(d * w for d, w in zip(base, weights))
        r = s % 11
        return 0 if r < 2 else 11 - r
    d1 = check(_CNPJ_WEIGHTS1)
    d2 = check(_CNPJ_WEIGHTS2)
    digits = "".join(str(d) for d in base) + str(d1) + str(d2)
    display = (f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}")
    return display, digits


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"NF-e nº {rng.randrange(1, 1000000):06d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def make_scenarios(cfg) -> dict:
    # cfg: [18, 12, 17] — ICMS rates by state (owner verifies)
    icms = [Decimal(str(r)) for r in cfg]
    pis = Decimal("1.65")     # OWNER: verify PIS/COFINS rates
    cofins = Decimal("7.6")
    return {
        "icms": {"mode": "exclusive", "rates": icms, "pick_one": True},
        "icms_pis_cofins": {"mode": "exclusive", "rates": icms, "pick_one": True,
                            "extra_lines": (("PIS", pis), ("COFINS", cofins))},
        "icms_incl": {"mode": "inclusive", "rates": icms, "pick_one": True},
    }


SPEC = CountrySpec(
    code="BR", name="Brazil", currency="BRL",
    native_lang="pt", scripts=("Latn",), font_stack=("Noto Sans",),
    number_style="european",
    tax_label="ICMS",
    vendors=(
        "Comercial Andrade Ltda.", "São Paulo Distribuidora S.A.", "Transporte Amazonia Ltda.",
        "Rio Informática Ltda.", "Belo Horizonte Papelaria Eireli", "Porto Alegre Alimentos Ltda.",
        "Curitiba Serviços de TI Ltda.", "Salvador Embalagens Ltda.",
    ),
    customers=(
        "Campinas Metalúrgica Ltda.", "Goiânia Atacado Ltda.", "Recife Comércio S.A.",
        "Florianópolis Varejo Ltda.", "Vitória Logística Ltda.",
    ),
    vendor_addresses=(
        ("Av. Paulista 1578, Bela Vista", "01310-200 São Paulo, SP"),
        ("Rua da Alfândega 66", "20070-000 Rio de Janeiro, RJ"),
        ("Av. do Contorno 6594, Savassi", "30110-044 Belo Horizonte, MG"),
        ("Rua Padre Chagas 342", "90570-080 Porto Alegre, RS"),
    ),
    customer_addresses=(
        ("Rod. Dom Pedro I, km 92", "13069-901 Campinas, SP"),
        ("Av. Anhanguera 4500", "74593-200 Goiânia, GO"),
        ("Av. Caxangá 2244", "50670-000 Recife, PE"),
    ),
    customer_tax_label="CNPJ / CPF",
    labels={
        "title": "FATURA", "invoice_no": "Nº da Nota", "invoice_date": "Data de emissão",
        "due_date": "Vencimento", "bill_to": "Cliente", "description": "Descrição",
        "qty": "Qtd", "unit_price": "Valor unit.", "amount": "Valor total",
        "subtotal": "Valor dos produtos", "total": "Valor total da nota",
        "payment_terms": "Condições de pagamento", "payment_account": "Conta para pagamento",
        "tax_id_label": "CNPJ",
    },
    tax_id_label_en="CNPJ",
    title_en="INVOICE",
    terms_native="Pagamento em {days} dias",
    terms_en="Payment within {days} days",
    tax_inclusive_note="Preços com ICMS incluído.",
    descriptions=(
        "Cadeira de escritório, tela, ergonômica",
        "Manutenção mensal — servidores e rede, suporte remoto incluído",
        "Frete: São Paulo → Rio de Janeiro, 2 paletes",
        "Licença de software — anual",
        "Papel A4 75g (caixa com 10 resmas)",
        "Serviços de contabilidade — mensal",
        "Tradução — português → inglês",
        "Catering corporativo — 20 pessoas",
        "Notebook i5, 16GB RAM, 512GB SSD",
        "Embalagens de papelão, caixa nº 4 (500 un.)",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Monthly maintenance — servers and network",
        "Freight São Paulo → Rio de Janeiro, 2 pallets",
        "Software license — annual",
        "Accounting services — monthly",
        "Cardboard boxes, size 4 (500 pcs)",
    ),
    units=(("un", "pcs"), ("h", "hrs"), ("cx", "boxes"), ("palete", "pallets")),
    price_range=(15, 2500),
    price_step=1,
    tax_id_gen=_cnpj,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "icms", "layout": "a", "lang": "native"},
        {"tax": "icms_pis_cofins", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "icms", "layout": "a", "lang": "native", "many_items": True},
        {"tax": "icms_pis_cofins", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "icms_incl", "layout": "b", "lang": "native"},
        {"tax": "icms", "layout": "a", "lang": "native"},
        {"tax": "icms_incl", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "icms", "layout": "b", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
    ),
)
