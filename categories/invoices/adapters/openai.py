"""OpenAI adapter (spec B3.2, B3.3) — shared prompt, native file input.

Chat Completions via plain REST (urllib, no SDK). PDFs ride a `file` content
part (inline base64); images use `image_url` data URIs. JSON mode on;
temperature 0 where the model accepts it (reasoning-class models may reject
the parameter — on that specific 400 we retry once without it, the API's own
default being the deterministic setting available).

Vendor docs verified 2026-09-20 (spec C3.4):
- Pricing/models: https://developers.openai.com/api/docs/pricing
  gpt-5.6-terra (current-gen mid-tier): $2.00/M in, $12.00/M out.
  Flagship gpt-6-astra ($10/$50) was considered and vetoed by the owner
  (cost); model is config-swappable via tool_models / OPENAI_MODEL.
- API shape: https://developers.openai.com/api/docs/api-reference/chat/create
  file part: {"type":"file","file":{"file_data":"<b64>","filename":...}};
  image_url part with data: URI; response_format json_object supported.
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

API_URL = "https://api.openai.com/v1/chat/completions"

DEFAULT_MODEL = "gpt-5.6-terra"
# USD per 1M tokens (verified 2026-09-20)
PRICE_TABLE = {
    "gpt-5.6-terra": (Decimal("2.00"), Decimal("12.00")),
    "gpt-5.6-sol": (Decimal("4.00"), Decimal("20.00")),
    "gpt-5.5": (Decimal("5.00"), Decimal("30.00")),
    "gpt-5.6-luna": (Decimal("0.20"), Decimal("1.20")),
}
_UNKNOWN_MODEL_PRICE = (Decimal("2.00"), Decimal("12.00"))

ASSUMED_IN_TOKENS = 1400        # prompt + one invoice page (PDF->tokens)
ASSUMED_OUT_TOKENS = 400

_MIME = {".pdf": "application/pdf", ".png": "image/png",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "extract_v1.md"


def load_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    _, sep, body = text.partition("\n---\n")
    return (body if sep else text).strip() + "\n"


class OpenAIAdapter:
    tool_id = "openai_chat"
    display_name = "OpenAI (GPT mid-tier)"

    def __init__(self, config: dict | None = None):
        tools_cfg = (config or {}).get("tool_models") or {}
        self.model = (os.environ.get("OPENAI_MODEL")
                      or tools_cfg.get(self.tool_id) or DEFAULT_MODEL)
        self._in_price, self._out_price = PRICE_TABLE.get(
            self.model, _UNKNOWN_MODEL_PRICE)

    def version(self) -> str:
        return self.model

    def estimate_cost(self, doc: DocFile) -> Decimal:
        cost = (Decimal(ASSUMED_IN_TOKENS) * self._in_price
                + Decimal(ASSUMED_OUT_TOKENS) * self._out_price) / 1_000_000
        return cost.quantize(Decimal("0.000001"))

    def _content_part(self, path: Path) -> dict:
        data = base64.b64encode(path.read_bytes()).decode()
        mime = _MIME[path.suffix.lower()]
        if mime == "application/pdf":
            return {"type": "file",
                    "file": {"file_data": f"data:{mime};base64,{data}",
                             "filename": path.name}}
        return {"type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"}}

    def _post(self, body: dict) -> dict:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set (.env or environment)")
        request = urllib.request.Request(
            API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(request, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504):
                detail = exc.read().decode("utf-8", "replace")[:200]
                raise TransientError(f"HTTP {exc.code}: {detail}") from exc
            raise RuntimeError(f"HTTP {exc.code}: {exc.read()[:500]!r}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise TransientError(f"network: {exc}") from exc

    def extract(self, doc: DocFile) -> RawResult:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": load_prompt()},
                self._content_part(doc.path),
            ]}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        t0 = time.perf_counter()
        try:
            payload = self._post(body)
        except RuntimeError as exc:
            # reasoning-class models may reject temperature; retry without it
            if "temperature" in str(exc):
                body.pop("temperature", None)
                payload = self._post(body)
            else:
                raise
        latency = (time.perf_counter() - t0) * 1000

        usage = payload.get("usage") or {}
        cost = (Decimal(int(usage.get("prompt_tokens", 0))) * self._in_price
                + Decimal(int(usage.get("completion_tokens", 0))) * self._out_price
                ) / 1_000_000
        return RawResult(payload=payload, latency_ms=latency, cost_usd=cost)

    def to_canonical(self, raw: RawResult) -> dict:
        choices = raw.payload.get("choices") or []
        text = ""
        if choices:
            text = (choices[0].get("message") or {}).get("content") or ""
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
