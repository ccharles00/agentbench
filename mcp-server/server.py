"""MCP server — stdio JSON-RPC transport over tools.py (spec B7).

Implements the MCP core surface (initialize / notifications/initialized /
tools/list / tools/call / ping) with no external SDK, so it runs anywhere
Python 3.11+ runs. The tool functions live in tools.py and read the static
JSON API built by `make build-api` — the server never calls vendor APIs.

Run:  python mcp-server/server.py [--site-dir SITE] [--results-dir RESULTS]
Configure (Claude etc.):
  { "command": "python", "args": ["<repo>/mcp-server/server.py",
      "--site-dir", "<repo>/site", "--results-dir", "<repo>/results"] }
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mcp_tools", _HERE / "tools.py")
tools_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tools_mod)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "agentbench-benchmark", "version": "0.1.0"}

TOOL_SPECS = [
    {"name": "list_categories", "description": "Categories benchmarked.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_tools", "description":
     "Tools benchmarked, with versions and test dates.",
     "inputSchema": {"type": "object", "properties": {
         "category": {"type": "string", "default": "invoices"}}}},
    {"name": "get_leaderboard", "description":
     "Leaderboard, optionally by dimension value (e.g. country=JP).",
     "inputSchema": {"type": "object", "properties": {
         "split": {"type": "string", "enum": ["public", "private"]},
         "dimension": {"type": "string"},
         "value": {"type": "string"},
         "category": {"type": "string"}}}},
    {"name": "recommend_extractor", "description":
     "Ranked invoice-extractor recommendation with confidence intervals.",
     "inputSchema": {"type": "object", "properties": {
         "countries": {"type": "array", "items": {"type": "string"}},
         "degradation": {"type": "string"},
         "max_cost_per_doc_usd": {"type": "number"},
         "min_exact_match": {"type": "number"},
         "split": {"type": "string", "enum": ["public", "private"]}}}},
    {"name": "get_failures", "description":
     "Examples of a tool's mistakes, filterable by country and field.",
     "inputSchema": {"type": "object", "required": ["tool_id"],
         "properties": {"tool_id": {"type": "string"},
                        "country": {"type": "string"},
                        "field": {"type": "string"},
                        "limit": {"type": "integer", "default": 5}}}},
]


def dispatch(name: str, args: dict, api, results_dir: Path):
    t = tools_mod
    if name == "list_categories":
        return t.list_categories(api)
    if name == "list_tools":
        return t.list_tools(api, args.get("category", "invoices"))
    if name == "get_leaderboard":
        return t.get_leaderboard(api, split=args.get("split", "public"),
                                 dimension=args.get("dimension"),
                                 value=args.get("value"),
                                 category=args.get("category", "invoices"))
    if name == "recommend_extractor":
        return t.recommend_extractor(
            api, countries=args.get("countries"),
            degradation=args.get("degradation"),
            max_cost_per_doc_usd=args.get("max_cost_per_doc_usd"),
            min_exact_match=args.get("min_exact_match"),
            split=args.get("split", "public"))
    if name == "get_failures":
        return {"failures": t.get_failures(
            api, results_dir, args["tool_id"], country=args.get("country"),
            field=args.get("field"), limit=args.get("limit", 5))}
    raise ValueError(f"unknown tool: {name}")


def serve(site_dir: Path, results_dir: Path) -> None:
    api = tools_mod.Api(site_dir)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method", "")
        msg_id = msg.get("id")
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            result = {"protocolVersion": PROTOCOL_VERSION,
                      "capabilities": {"tools": {}},
                      "serverInfo": SERVER_INFO}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOL_SPECS}
        elif method == "tools/call":
            try:
                out = dispatch(msg["params"]["name"],
                               msg["params"].get("arguments") or {},
                               api, results_dir)
                result = {"content": [{"type": "text",
                                       "text": json.dumps(out, ensure_ascii=False)}]}
            except Exception as exc:                    # tool-level error
                result = {"content": [{"type": "text",
                                       "text": f"error: {exc}"}],
                          "isError": True}
        else:
            if msg_id is None:
                continue
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": msg_id,
                 "error": {"code": -32601, "message": f"method not found: {method}"}
                 }) + "\n")
            sys.stdout.flush()
            continue
        if msg_id is not None:
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
            sys.stdout.flush()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--site-dir", default=str(_HERE.parent / "site"))
    p.add_argument("--results-dir", default=str(_HERE.parent / "results"))
    a = p.parse_args()
    serve(Path(a.site_dir), Path(a.results_dir))


if __name__ == "__main__":
    main()
