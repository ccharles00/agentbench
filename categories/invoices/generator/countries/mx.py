"""MX invoices: Spanish, IVA 16%, structurally valid RFC, CLABE accounts.

Retention docs (DECISIONS.md #18): persona física vendors (person's name,
13-char RFC) with ISR retention 10% + IVA retention 2/3 of IVA charged,
printed as two lines and summed into unscored `withholding_total`.
"""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids
from ..build import CountrySpec

_ABC = "ABCDEFGHJKLMNPRSTUVWXYZ"   # RFC letters; Ñ excluded for simplicity


def _rfc_for(name: str, fisica: bool = False) -> str:
    """Structurally valid RFC derived stably from the vendor name (#20).

    12 chars for personas morales (3 letters + YYMMDD + homoclave), 13 for
    personas físicas (4 letters). The embedded date is valid.
    """
    rng = ids.stable_rng("RFC:" + name)
    letters = "".join(ch for ch in name.upper() if ch in _ABC)
    n_letters = 4 if fisica else 3
    code_letters = (letters[:n_letters] +
                    "".join(rng.choice(_ABC) for _ in range(n_letters)))[:n_letters]
    year = rng.randrange(1965, 1996) if fisica else rng.randrange(2010, 2025)
    d = date(year, rng.randrange(1, 13), rng.randrange(1, 29))
    homoclave = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(3))
    return f"{code_letters}{d:%y%m%d}{homoclave}"


def _structural_tax_id(name: str) -> tuple[str, str]:
    rfc = _rfc_for(name, fisica=False)
    return rfc, rfc


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"FOLIO-{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def make_scenarios(cfg) -> dict:
    iva = Decimal(str(cfg[0]))  # 16
    return {
        "iva16": {"mode": "exclusive", "rates": [iva]},
        # ISR retention 10% + IVA retention (2/3 of IVA charged) — #18
        "iva16_ret": {"mode": "exclusive", "rates": [iva], "withholding": Decimal("10")},
    }


SPEC = CountrySpec(
    code="MX", name="Mexico", currency="MXN",
    native_lang="es", scripts=("Latn",), font_stack=("Noto Sans",),
    page_size="Letter",
    numeric_dates=True,
    tax_label="IVA",
    vendors=(
        "Distribuidora del Norte S.A. de C.V.", "Grupo Comercial Bajío S. de R.L.",
        "Servicios Corporativos Zapata S.C.", "Manufacturas Monterrey S.A.",
        "Tecnología del Valle S.A. de C.V.", "Logística Pacífico S. de R.L.",
        "Alimentos Central Mexicanos S.A.", "Papelería Industrial Guadalajara S.A.",
    ),
    vendors_fisica=(
        "Maria Fernanda Lopez Salgado", "Jose Antonio Ramirez Cuellar",
        "Laura Elena Vargas Molina", "Carlos Humberto Torres Pineda",
    ),
    customers=(
        "Constructora Peña Blanca S.A. de C.V.", "Comercializadora Veracruz S. de R.L.",
        "Industrias Querétaro S.A.", "Servicios Tápicos del Bajío S.C.",
    ),
    vendor_addresses=(
        ("Av. Insurgentes Sur 1234, Col. Del Valle", "03100 Ciudad de México, CDMX"),
        ("Av. Constitución 456 Ote., Col. Centro", "64000 Monterrey, NL"),
        ("Blvd. Avila Camacho 1230, Col. Reforma", "72050 Puebla, PUE"),
        ("Av. Vallarta 3045, Col. Arcos Vallarta", "44500 Guadalajara, JAL"),
    ),
    customer_addresses=(
        ("Calle Reforma 210, Col. Centro", "06000 Ciudad de México, CDMX"),
        ("Av. Juárez 88, Col. Centro", "68000 Oaxaca, OAX"),
        ("Carretera Nacional km 12, Col. Las Torres", "64960 Monterrey, NL"),
    ),
    customer_tax_label="RFC",
    labels={
        "title": "FACTURA", "invoice_no": "Folio", "invoice_date": "Fecha de emisión",
        "due_date": "Fecha de vencimiento", "bill_to": "Cliente", "description": "Concepto",
        "qty": "Cantidad", "unit_price": "Precio unit.", "amount": "Importe",
        "subtotal": "Subtotal", "total": "Total",
        "payment_terms": "Condiciones de pago", "payment_account": "Cuenta CLABE",
        "tax_id_label": "RFC",
    },
    tax_id_label_en="RFC",
    title_en="INVOICE",
    terms_native="Pago a {days} días",
    terms_en="Payment within {days} days",
    descriptions=(
        "Silla de oficina, malla, ergonómica",
        "Mantenimiento mensual — servidores y red, soporte remoto incluido",
        "Flete: CDMX → Monterrey, 2 tarimas",
        "Licencia de software — anual",
        "Papel bond carta (caja de 10 resmas)",
        "Servicios de contabilidad — mensual",
        "Traducción — español → inglés",
        "Catering corporativo — 20 personas",
        "Equipo de cómputo, laptop i5, 16GB RAM",
        "Suministros de papelería — paquete anual",
    ),
    descriptions_english=(
        "Office chairs, mesh, ergonomic",
        "Monthly maintenance — servers and network",
        "Freight CDMX → Monterrey, 2 pallets",
        "Software license — annual",
        "Accounting services — monthly",
        "Stationery supplies — annual package",
    ),
    units=(("pza", "pcs"), ("h", "hrs"), ("caja", "boxes"), ("tarima", "pallets")),
    price_range=(50, 8000),
    price_step=1,
    use_clabe=True,
    structural_tax_id=_structural_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "iva16", "layout": "a", "lang": "native"},
        {"tax": "iva16", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "iva16", "layout": "a", "lang": "native", "many_items": True},
        {"tax": "iva16_ret", "layout": "c", "lang": "native", "ambiguous_date": True,
         "fisica": True},
        {"tax": "iva16", "layout": "b", "lang": "english", "cross_border": True,
         "currency": "USD", "symbol_mode": "code"},
        {"tax": "iva16", "layout": "a", "lang": "native"},
        {"tax": "iva16_ret", "layout": "b", "lang": "native", "fisica": True},
        {"tax": "iva16", "layout": "c", "lang": "native", "ambiguous_date": True},
    ),
)
