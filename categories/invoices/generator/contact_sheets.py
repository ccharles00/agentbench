"""Contact sheets for human visual review (spec B2.8).

Per country: a grid of first-page thumbnails from the clean PDFs, plus one
"variants" sheet showing how scan / bad_scan / phone_photo degrade the first
document. Written to <split>/contact_sheets/.

Rendered at review resolution (1000px-wide thumbnails, 2 columns) so the
owner can actually read them zoomed in; sheets are gitignored review
artifacts, so file size is not a concern.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

THUMB_WIDTH = 1000
COLS = 2
LABEL_H = 46


def _font() -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=30)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def _page_thumbnail(pdf_path: Path, width: int = THUMB_WIDTH) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[0]
    zoom = width / page.rect.width
    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    doc.close()
    return img


def _labeled(img: Image.Image, label: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + LABEL_H), "white")
    out.paste(img, (0, 0))
    ImageDraw.Draw(out).text((6, img.height + 3), label, fill="black", font=_font())
    return out


def _country_sheet(split_dir: Path, country: str, doc_ids: list[str]) -> Path:
    tiles = []
    for doc_id in doc_ids:
        pdf = split_dir / "documents" / doc_id / "clean.pdf"
        tiles.append(_labeled(_page_thumbnail(pdf), doc_id))
    rows = (len(tiles) + COLS - 1) // COLS
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (COLS * (tw + 8) + 8, rows * (th + 8) + 8), "#e8e8e8")
    for i, tile in enumerate(tiles):
        r, c = divmod(i, COLS)
        sheet.paste(tile, (8 + c * (tw + 8), 8 + r * (th + 8)))
    out = split_dir / "contact_sheets" / f"{country}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="PNG")
    return out


def _variants_sheet(split_dir: Path, doc_id: str) -> Path:
    doc_dir = split_dir / "documents" / doc_id
    tiles = []
    for label, path in (
        ("clean_pdf", doc_dir / "clean.pdf"),
        ("scan", doc_dir / f"{doc_id}_scan.png"),
        ("bad_scan", doc_dir / f"{doc_id}_bad_scan.jpg"),
        ("phone_photo", doc_dir / f"{doc_id}_phone_photo.jpg"),
    ):
        if not path.exists():
            continue
        img = (_page_thumbnail(path) if path.suffix == ".pdf"
               else Image.open(path).convert("RGB"))
        img.thumbnail((THUMB_WIDTH, 10_000))
        tiles.append(_labeled(img, f"{doc_id} · {label}"))
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (len(tiles) * (tw + 8) + 8, th + 16), "#e8e8e8")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (8 + i * (tw + 8), 8))
    out = split_dir / "contact_sheets" / f"{doc_id}_variants.png"
    sheet.save(out, format="PNG")
    return out


def make_all(split_dir: Path) -> list[Path]:
    """Build one sheet per country (from manifest order) + one variants sample sheet."""
    import json
    manifest = json.loads((split_dir / "manifest.json").read_text(encoding="utf-8"))
    by_country: dict[str, list[str]] = {}
    for entry in manifest["documents"]:
        by_country.setdefault(entry["country"], []).append(entry["doc_id"])
    outs = []
    for country, doc_ids in sorted(by_country.items()):
        outs.append(_country_sheet(split_dir, country, doc_ids))
    if manifest["documents"]:
        first = sorted(by_country)[0]
        outs.append(_variants_sheet(split_dir, by_country[first][0]))
    return outs
