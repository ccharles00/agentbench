"""DE invoices: comma decimals, period thousands, USt 19%/7%, reverse charge, IBAN."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

from .. import ids, money
from ..build import CountrySpec


def _tax_id(rng: random.Random, name: str) -> tuple[str, str]:
    digits = ids.random_digits(rng, 9)
    return f"DE {digits[:3]} {digits[3:6]} {digits[6:]}", f"DE{digits}"


def _invoice_no(rng: random.Random, d: date) -> str:
    return f"RE-{d.year}-{rng.randrange(1, 10000):04d}"


def _date(d: date, lang_mode: str, digits: str) -> str:
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def make_scenarios(cfg) -> dict:
    std = Decimal(str(cfg[0]))   # 19
    reduced = Decimal(str(cfg[1]))  # 7
    return {
        "std19": {"mode": "exclusive", "rates": [std]},
        "mixed": {"mode": "exclusive", "rates": [std, reduced], "mixed": True,
                  "labels": {money.fmt_rate(std): "USt",
                             money.fmt_rate(reduced): "USt (reduced)"}},
        "reverse_charge": {"mode": "reverse_charge", "rates": [Decimal("0")],
                           "line_label": "USt 0% (Reverse Charge)"},
    }


SPEC = CountrySpec(
    code="DE", name="Germany", currency="EUR",
    native_lang="de", scripts=("Latn",), font_stack=("Noto Sans",),
    number_style="european",
    numeric_dates=True,
    tax_label="USt",
    vendors=(
        "Müller & Schulze GmbH", "Berliner Bürobedarf e.K.", "Hanseatische Logistik AG",
        "Schwarzwald Elektro GmbH", "Rhein Main Consulting GmbH", "Alpen Tech Solutions KG",
        "Nordsee Fischhandel GmbH", "Frankfurter Steuerberatung Dr. Weiss",
    ),
    customers=(
        "Leipzig Handels GmbH", "Stuttgart Metallbau GmbH", "Dresdner Baustoffe GmbH",
        "Kölner Medienhaus GmbH", "Hamburger Werftlogistik GmbH", "Nürnberger Präzisionstechnik GmbH",
    ),
    vendor_addresses=(
        ("Musterstraße 12", "10115 Berlin"),
        ("Hafenstraße 48", "20359 Hamburg"),
        ("Königsallee 55", "40212 Düsseldorf"),
        ("Bahnhofstraße 7", "60313 Frankfurt am Main"),
        ("Marienplatz 3", "80331 München"),
    ),
    customer_addresses=(
        ("Lindenweg 20", "04109 Leipzig"),
        ("Neckarstraße 66", "70190 Stuttgart"),
        ("Elballee 14", "01067 Dresden"),
        ("Hohenzollernring 52", "50672 Köln"),
    ),
    customer_tax_label="USt-IdNr.",
    labels={
        "title": "RECHNUNG", "invoice_no": "Rechnungs-Nr.", "invoice_date": "Rechnungsdatum",
        "due_date": "Fällig am", "bill_to": "Rechnung an", "description": "Beschreibung",
        "qty": "Menge", "unit_price": "Einzelpreis", "amount": "Betrag",
        "subtotal": "Nettobetrag", "total": "Gesamtbetrag",
        "payment_terms": "Zahlungsbedingungen", "payment_account": "IBAN",
        "tax_id_label": "USt-IdNr.",
    },
    tax_id_label_en="USt-IdNr.",
    title_en="INVOICE",
    terms_native="Zahlbar innerhalb von {days} Tagen",
    terms_en="Payment within {days} days",
    reverse_charge_note="Reverse Charge — Steuerschuldnerschaft des Leistungsempfängers (§ 13b UStG)",
    descriptions=(
        "Bürostuhl, Netzstoff, ergonomisch",
        "Monatliche Wartung — Klimaanlage, inklusive Ersatzteilen und Notdienst",
        "Transport Hamburg → München, 2 Paletten, Kombi-Verkehr",
        "Softwarelizenz, Jahresabo, 5 Arbeitsplätze",
        "Steuerberatung — Quartalsabschluss",
        "Druck: Produktkatalog, 4-farbig, 500 Stück, Rückenklebung",
        "Brötchen und Backwaren, Lieferung wöchentlich",
        "Fachbuch: Grundlagen der Buchführung, 3. Auflage",
        "Elektroinstallation — Objekt 12, GruppeVerteilung und Zählerplatz",
        "IT-Support-Stunden, remote",
        "Lagerservice — Kommissionierung, 3 Monate",
        "Übersetzung DE → EN, technisches Handbuch, 40 Seiten",
    ),
    descriptions_english=(
        "Office chair, mesh, ergonomic",
        "Monthly maintenance — HVAC systems, including spare parts",
        "Freight Hamburg → Munich, 2 pallets",
        "Software license — annual subscription, 5 seats",
        "Tax consulting — quarterly closing",
        "Printing: product catalogue, 4-colour, 500 copies",
        "IT support hours, remote",
        "Translation DE → EN, technical manual, 40 pages",
    ),
    units=(("Stk.", "pcs"), ("Std.", "hrs"), ("kg", "kg"), ("Pauschale", "flat")),
    price_range=(10, 1200),
    price_step=1,
    iban_spec=("DE", 18),
    tax_id_gen=_tax_id,
    invoice_no_gen=_invoice_no,
    date_render=_date,
    doc_plan=(
        {"tax": "std19", "layout": "a", "lang": "native"},
        {"tax": "mixed", "layout": "b", "lang": "native", "symbol_mode": "both"},
        {"tax": "std19", "layout": "a", "lang": "native"},
        {"tax": "mixed", "layout": "c", "lang": "native", "ambiguous_date": True},
        {"tax": "reverse_charge", "layout": "a", "lang": "english", "cross_border": True,
         "symbol_mode": "code"},
        {"tax": "std19", "layout": "b", "lang": "native"},
        {"tax": "mixed", "layout": "a", "lang": "native", "many_items": True},
        {"tax": "std19", "layout": "c", "lang": "native", "ambiguous_date": True},
    ),
)
