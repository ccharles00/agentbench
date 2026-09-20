"""Google Gemini adapter — the first real extractor (spec B3.2, B3.3).

Uses the shared extraction prompt (prompts/extract_v1.md, published on the
methodology page), temperature 0, JSON response mode, and passes each
document file natively (PDF/PNG/JPEG inline base64).

Vendor docs verified 2026-09-20 (spec C3.4 — record URL + date):
- Models:      https://ai.google.dev/gemini-api/docs/models
               gemini-3.8-flash = latest stable Flash (no stable Gemini 3 Pro;
               gemini-2.5-pro is the stable Pro-class option)
- Pricing:     https://ai.google.dev/gemini-api/docs/pricing
               gemini-3.8-flash standard tier: $0.75/M input, $3.75/M output
               (promo through 2026-12-31, then $1.50/$7.50 — revisit then)
- PDFs:        https://ai.google.dev/gemini-api/docs/document-processing
               inline base64, billed as image/DOCUMENT tokens (~258/page)
- API shape:   https://ai.google.dev/api/generate-content
               POST v1beta/models/{model}:generateContent, camelCase fields,
               x-goog-api-key header (key never in URLs or logs)

Model ID comes from config.yaml (spec B3.2: never hardcoded) with a
GEMINI_MODEL env override. Free tier exists but trains on content and rate
limits aggressively; our documents are synthetic either way.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

from core.harness.adapter_base import DocFile, RawResult, TransientError

API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "{model}:generateContent")

DEFAULT_MODEL = "gemini-3.8-flash"
# gemini-3.8-flash standard-tier rates, USD per 1M tokens (verified 2026-09-20)
INPUT_PER_MTOK = Decimal("0.75")
OUTPUT_PER_MTOK = Decimal("3.75")

# Cost estimate assumptions (before we know real usage):
PDF_TOKENS_PER_PAGE = 258          # docs' figure for text-heavy pages
ASSUMED_PAGES = 2                  # most docs are 1 page; 13/104 are multipage
ASSUMED_OUTPUT_TOKENS = 400

_MIME = {".pdf": "application/pdf", ".png": "image/png",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "extract_v1.md"


def load_prompt() -> str:
    """The prompt body — everything after the metadata separator line."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    _, sep, body = text.partition("\n---\n")
    if not sep:
        return text
    return body.strip() + "\n"


class GeminiAdapter:
    tool_id = "google_gemini_flash"
    display_name = "Google Gemini (Flash)"

    def __init__(self, config: dict | None = None):
        tools_cfg = (config or {}).get("tool_models") or {}
        self.model = (os.environ.get("GEMINI_MODEL")
                      or tools_cfg.get(self.tool_id) or DEFAULT_MODEL)

    def version(self) -> str:
        return self.model

    def estimate_cost(self, doc: DocFile) -> Decimal:
        prompt_tokens = len(load_prompt()) // 4     # rough chars->tokens
        in_tokens = prompt_tokens + PDF_TOKENS_PER_PAGE * ASSUMED_PAGES
        cost = (Decimal(in_tokens) * INPUT_PER_MTOK
                + Decimal(ASSUMED_OUTPUT_TOKENS) * OUTPUT_PER_MTOK) / 1_000_000
        return cost.quantize(Decimal("0.000001"))

    def extract(self, doc: DocFile) -> RawResult:
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set (.env or environment)")

        data = doc.path.read_bytes()
        mime = _MIME.get(doc.path.suffix.lower())
        if mime is None:
            raise RuntimeError(f"unsupported file type: {doc.path.name}")

        body = json.dumps({
            "contents": [{
                "parts": [
                    {"text": load_prompt()},
                    {"inlineData": {"mimeType": mime,
                                    "data": base64.b64encode(data).decode()}},
                ]}],
            "generationConfig": {"temperature": 0,
                                 "responseMimeType": "application/json"},
        }).encode("utf-8")

        request = urllib.request.Request(
            API_URL.format(model=self.model), data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": key})

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=180) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504):
                detail = exc.read().decode("utf-8", "replace")[:200]
                raise TransientError(f"HTTP {exc.code}: {detail}") from exc
            raise RuntimeError(f"HTTP {exc.code}: {exc.read()[:500]!r}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise TransientError(f"network: {exc}") from exc
        latency = (time.perf_counter() - t0) * 1000

        usage = payload.get("usageMetadata") or {}
        cost = (Decimal(int(usage.get("promptTokenCount", 0))) * INPUT_PER_MTOK
                + Decimal(int(usage.get("candidatesTokenCount", 0)))
                * OUTPUT_PER_MTOK) / 1_000_000

        return RawResult(payload=payload, latency_ms=latency, cost_usd=cost)

    def to_canonical(self, raw: RawResult) -> dict:
        """Map Gemini's JSON answer to our field names — no value fixing (B3.1)."""
        candidates = raw.payload.get("candidates") or []
        text = ""
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        out = {}
        for key, value in parsed.items():
            if key == "line_item_count" and value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    pass
            out[key] = value
        return out
