"""HTML -> PDF via headless Chromium, then rasterization (spec B2.1, B2.4).

Chromium is used because it shapes complex scripts (Arabic, Indic), runs
bidi correctly, and embeds proper ToUnicode maps so the text layer is
extractable — ReportLab-class libraries do none of that reliably.

Fonts are loaded through local @font-face file:// URIs pinned by fonts.lock.
"""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

GENERATOR_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = GENERATOR_DIR / "templates"
FONTS_LOCK = GENERATOR_DIR / "fonts.lock"

_font_face_cache: str | None = None


def font_face_css() -> str:
    """@font-face rules pointing at the pinned font files (fonts.lock)."""
    global _font_face_cache
    if _font_face_cache is not None:
        return _font_face_cache
    lock = json.loads(FONTS_LOCK.read_text(encoding="utf-8"))
    rules = []
    for family, meta in lock["fonts"].items():
        path = (GENERATOR_DIR / "fonts" / meta["file"]).as_uri()
        rules.append(
            f"@font-face {{ font-family: '{family}'; "
            f"src: url('{path}') format('truetype-variations'); "
            f"font-weight: 100 900; font-style: normal; }}")
    _font_face_cache = "\n".join(rules)
    return _font_face_cache


def build_html(inv) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)
    template = env.get_template("base.html.j2")
    items = [
        {
            "description": it.description,
            "quantity": it.quantity,
            "unit": it.unit,
            "unit_price_display": it.unit_price_display,
            "amount_display": it.amount_display,
            "tax_rate_display": f"{it.tax_rate.normalize():f}%" if it.tax_rate is not None else "",
            "tax_display": it.tax_display or "",
        }
        for it in inv.items
    ]
    return template.render(
        doc_id=inv.doc_id,
        lang=inv.language[0],
        direction=inv.direction,
        page_size=inv.page_size,
        font_face_css=font_face_css(),
        font_stack_css=inv.font_stack_css,
        accent=f"hsl({inv.logo_hue},48%,38%)" if inv.template_style != "fapiao" else "#b91c1c",
        layout=inv.layout,
        template_style=inv.template_style,
        logo_svg=inv.logo_svg,
        title=inv.title,
        labels=inv.labels,
        invoice_number=inv.invoice_number,
        invoice_date=inv.rendered_strings["invoice_date"],
        due_date_display=inv.rendered_strings.get("due_date"),
        customer_name=inv.customer_name,
        customer_address_lines=inv.customer_address_lines,
        customer_tax_id_label=inv.customer_tax_id_label,
        customer_tax_id_display=inv.customer_tax_id_display,
        vendor=inv.vendor,
        items=items,
        subtotal_rows=inv.subtotal_rows,
        tax_rows=[{"label": tl.label, "display": tl.amount_display} for tl in inv.tax_lines],
        total_display=inv.total_display,
        dual_currency_line=inv.dual_currency_line,
        amount_in_words=inv.amount_in_words,
        words_label=inv.words_label,
        payment_terms_display=inv.payment_terms_display,
        account_display=inv.account_display,
        bank_lines=inv.bank_lines,
        notes=inv.notes,
        qr_data_uri=inv.qr_payload,
    )


class PdfRenderer:
    """One Chromium instance reused for the whole run (much faster)."""

    def __init__(self) -> None:
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            args=["--force-color-profile=srgb", "--font-render-hinting=none"])
        self._page = self._browser.new_page()

    def render(self, html_path: Path, out_pdf: Path, page_size: str) -> None:
        self._page.goto(html_path.as_uri(), wait_until="load")
        self._page.evaluate("() => document.fonts.ready")
        self._page.pdf(
            path=str(out_pdf), print_background=True,
            format=("A4" if page_size == "A4" else "Letter"),
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()
