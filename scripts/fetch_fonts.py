"""Download the pinned Google Noto fonts used for rendering (spec B2.1).

Reproducibility: the fonts.lock file pins the google/fonts commit and the
SHA256 of every font file. If fonts.lock exists, downloads are verified
against it; otherwise the current default branch commit is resolved and
recorded. The fonts directory is gitignored; fonts.lock is committed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

GENERATOR_DIR = Path(__file__).resolve().parents[1] / "categories" / "invoices" / "generator"
FONTS_DIR = GENERATOR_DIR / "fonts"
LOCK_PATH = GENERATOR_DIR / "fonts.lock"

# family name (as used in CSS @font-face) -> path in the google/fonts repo
FONT_FILES = {
    "Noto Sans": "ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf",
    "Noto Sans SC": "ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
    "Noto Sans JP": "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf",
    "Noto Sans KR": "ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
    "Noto Naskh Arabic": "ofl/notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf",
    "Noto Sans Devanagari": "ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth,wght%5D.ttf",
    "Noto Sans Thai": "ofl/notosansthai/NotoSansThai%5Bwdth,wght%5D.ttf",
}
FALLBACK_COMMIT = "f83f1c33731f5b2f2cf3f0ea94e3f9b3d0e2cf3a"  # only if lock missing AND API unreachable


def resolve_commit() -> str:
    pinned = os.environ.get("GOOGLE_FONTS_COMMIT", "").strip()
    if pinned:
        return pinned
    try:
        with urllib.request.urlopen(
                "https://api.github.com/repos/google/fonts/commits/main", timeout=30) as resp:
            return json.load(resp)["sha"]
    except OSError as exc:
        print(f"WARNING: could not resolve google/fonts HEAD ({exc}); "
              f"using fallback commit {FALLBACK_COMMIT}", file=sys.stderr)
        return FALLBACK_COMMIT


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    lock = None
    if LOCK_PATH.exists():
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        commit = lock["commit"]
        print(f"Using pinned commit from fonts.lock: {commit[:12]}")
    else:
        commit = resolve_commit()

    changed = lock is None or lock.get("commit") != commit
    for family, repo_path in FONT_FILES.items():
        url = f"https://raw.githubusercontent.com/google/fonts/{commit}/{repo_path}"
        filename = repo_path.rsplit("/", 1)[-1]
        out_path = FONTS_DIR / filename
        expected = (lock or {}).get("fonts", {}).get(family, {}).get("sha256")
        if out_path.exists() and expected and sha256_of(out_path) == expected:
            print(f"  ok (cached): {family}")
            continue
        print(f"  downloading {family} ...")
        urllib.request.urlretrieve(url, out_path)
        digest = sha256_of(out_path)
        if expected and digest != expected:
            out_path.unlink()
            raise SystemExit(
                f"SHA256 mismatch for {family}: expected {expected}, got {digest}. "
                "Refusing to use unverified fonts.")
        changed = True

    # (Re)write the lock with verified hashes.
    if changed or not LOCK_PATH.exists():
        fonts = {}
        for family, repo_path in FONT_FILES.items():
            filename = repo_path.rsplit("/", 1)[-1]
            fonts[family] = {"file": filename, "sha256": sha256_of(FONTS_DIR / filename)}
        LOCK_PATH.write_text(
            json.dumps({"commit": commit, "fonts": fonts}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print(f"Wrote {LOCK_PATH}")
    print("Fonts ready.")


if __name__ == "__main__":
    main()
