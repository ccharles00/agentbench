"""Deterministic degradation of clean PDFs (spec B2.4).

Variants:
  scan        — rasterized, slight rotation, mild noise, 200 DPI, grayscale, no text layer
  bad_scan    — heavier noise, blur, ~150 DPI, stamp overlapping text, JPEG artifacts
  phone_photo — perspective warp, uneven lighting, background margin, JPEG

Every effect is driven by a NumPy RNG seeded per (doc, variant, page), so the
same seed regenerates the same pixels. Output: scan -> PNG, bad_scan and
phone_photo -> JPEG (as specified).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import pymupdf as fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

GENERATOR_DIR = Path(__file__).resolve().parent


@dataclass
class VariantFile:
    variant: str     # clean_pdf | scan | bad_scan | phone_photo
    page: int        # 0-based
    path: Path


def _open(pdf_path: Path) -> fitz.Document:
    return fitz.open(pdf_path)


def _rasterize(doc: fitz.Document, page_index: int, dpi: int, gray: bool) -> Image.Image:
    cs = fitz.csGRAY if gray else fitz.csRGB
    pm = doc[page_index].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), colorspace=cs, alpha=False)
    mode = "L" if gray else "RGB"
    return Image.frombytes(mode, (pm.width, pm.height), pm.samples)


def _font() -> ImageFont.FreeTypeFont:
    import json
    lock = json.loads((GENERATOR_DIR / "fonts.lock").read_text(encoding="utf-8"))
    path = GENERATOR_DIR / "fonts" / lock["fonts"]["Noto Sans"]["file"]
    return ImageFont.truetype(str(path), size=64)


def _add_noise(img: np.ndarray, rng: np.random.Generator, sigma: float) -> np.ndarray:
    noise = rng.normal(0.0, sigma, img.shape)
    return np.clip(img.astype(np.float64) + noise, 0, 255).astype(np.uint8)


def _rescale(img: Image.Image, factor: float) -> Image.Image:
    # simulate lower scanner resolution by resampling down and back up
    w, h = img.size
    small = img.resize((max(1, int(w * factor)), max(1, int(h * factor))), Image.BILINEAR)
    return small.resize((w, h), Image.BILINEAR)


def _add_stamp(img: Image.Image, rng: np.random.Generator) -> Image.Image:
    w, h = img.size
    overlay = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(overlay)
    text = ["PAID", "RECEIVED", "COPY", "VOID"][int(rng.integers(0, 4))]
    value = int(rng.integers(90, 140))          # gray ink value
    x = int(rng.integers(w * 0.25, max(w * 0.25 + 1, w * 0.55)))
    y = int(rng.integers(h * 0.30, max(h * 0.30 + 1, h * 0.70)))
    draw.text((x, y), text, fill=value, font=_font())
    bbox_pad = 18
    draw.ellipse((x - bbox_pad, y - bbox_pad, x + 300, y + 84), outline=value, width=6)
    angle = float(rng.uniform(-12, 12))
    overlay = overlay.rotate(angle, expand=False, fillcolor=255, resample=Image.BICUBIC)
    # stamp is dark where the overlay is dark; composite via inverted mask
    mask = Image.eval(overlay, lambda p: 255 - p)
    dark = Image.new("L", (w, h), value)
    return Image.composite(dark, img, mask)


def _scan(img: Image.Image, rng: np.random.Generator, out: Path) -> None:
    im = img.rotate(float(rng.uniform(0.3, 3.0)) * (1 if rng.random() < 0.5 else -1),
                    expand=True, resample=Image.BICUBIC, fillcolor=255)
    arr = _add_noise(np.asarray(im), rng, rng.uniform(3.5, 7.0))
    gain = float(rng.uniform(0.95, 1.05))
    arr = np.clip(arr.astype(np.float64) * gain, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(out, format="PNG")


def _bad_scan(img: Image.Image, rng: np.random.Generator, out: Path) -> None:
    im = img.rotate(float(rng.uniform(0.8, 3.5)) * (1 if rng.random() < 0.5 else -1),
                    expand=True, resample=Image.BICUBIC, fillcolor=255)
    im = _rescale(im, float(rng.uniform(0.62, 0.75)))
    arr = _add_noise(np.asarray(im), rng, rng.uniform(9.0, 14.0))
    arr = cv2.GaussianBlur(arr, (0, 0), float(rng.uniform(1.1, 1.9)))
    arr = np.clip(arr.astype(np.float64) * float(rng.uniform(0.86, 0.98)), 0, 255).astype(np.uint8)
    stamped = _add_stamp(Image.fromarray(arr), rng)
    stamped.save(out, format="JPEG", quality=int(rng.integers(36, 54)))


def _phone_photo(img: Image.Image, rng: np.random.Generator, out: Path) -> None:
    src = cv2.cvtColor(np.asarray(img), cv2.COLOR_GRAY2RGB if img.mode == "L" else cv2.COLOR_RGB2BGR)
    h, w = src.shape[:2]

    # perspective warp: pull corners inward by a few percent
    off_x = lambda: w * rng.uniform(0.015, 0.045)
    off_y = lambda: h * rng.uniform(0.015, 0.045)
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst_pts = np.float32([
        [off_x(), off_y()], [w - off_x(), off_y()],
        [w - off_x(), h - off_y()], [off_x(), h - off_y()],
    ])
    warped = cv2.warpPerspective(src, cv2.getPerspectiveTransform(src_pts, dst_pts),
                                 (w, h), borderValue=(255, 255, 255))

    # uneven lighting: linear gradient multiplier across the page
    gradient = np.linspace(rng.uniform(0.68, 0.85), rng.uniform(1.0, 1.12), h)[:, None, None]
    warped = np.clip(warped.astype(np.float64) * gradient, 0, 255).astype(np.uint8)

    # background margin (desk), then paste the page with a soft shadow
    page_img = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
    margin_x, margin_y = int(w * rng.uniform(0.05, 0.09)), int(h * rng.uniform(0.04, 0.07))
    canvas = Image.new("RGB", (w + 2 * margin_x, h + 2 * margin_y),
                       (int(rng.integers(150, 190)),) * 3)
    shadow = Image.new("L", page_img.size, 0)
    ImageDraw.Draw(shadow).rectangle(
        (6, 8, page_img.size[0] + 6, page_img.size[1] + 8), fill=70)
    canvas.paste(Image.new("RGB", page_img.size, (60, 60, 60)),
                 (margin_x + 6, margin_y + 8), shadow.filter(ImageFilter.GaussianBlur(8)))
    canvas.paste(page_img, (margin_x, margin_y))
    canvas.save(out, format="JPEG", quality=int(rng.integers(55, 72)))


def make_variants(pdf_path: Path, out_dir: Path, doc_id: str,
                  seed: int) -> list[VariantFile]:
    """Produce scan / bad_scan / phone_photo from a clean PDF. Deterministic."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = _open(pdf_path)
    made: list[VariantFile] = []
    for page_index in range(len(doc)):
        suffix = f"_p{page_index + 1}" if len(doc) > 1 else ""
        # scan
        rng = np.random.default_rng([seed, page_index, 1])
        img = _rasterize(doc, page_index, 200, gray=True)
        p = out_dir / f"{doc_id}_scan{suffix}.png"
        _scan(img, rng, p)
        made.append(VariantFile("scan", page_index, p))
        # bad_scan
        rng = np.random.default_rng([seed, page_index, 2])
        img = _rasterize(doc, page_index, 150, gray=True)
        p = out_dir / f"{doc_id}_bad_scan{suffix}.jpg"
        _bad_scan(img, rng, p)
        made.append(VariantFile("bad_scan", page_index, p))
        # phone_photo
        rng = np.random.default_rng([seed, page_index, 3])
        img = _rasterize(doc, page_index, 170, gray=True)
        p = out_dir / f"{doc_id}_phone_photo{suffix}.jpg"
        _phone_photo(img, rng, p)
        made.append(VariantFile("phone_photo", page_index, p))
    doc.close()
    return made
