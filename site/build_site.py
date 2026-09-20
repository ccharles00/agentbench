"""Static site generator (spec B5) — scaffold: leaderboard home page.

The full M3 build expands this into heatmap, failure gallery, tool pages,
methodology, neutrality policy, API docs and corrections log. This scaffold
proves the results-to-HTML pipeline and gives the deploy target something
real to serve.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.config import ROOT


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 16px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 980px;
       padding: 2rem 1rem 4rem; }
h1 { font-size: 1.5rem; } .sub { opacity: .75; margin-top: -0.5rem; }
table { border-collapse: collapse; width: 100%; margin: 1.5rem 0; }
th, td { padding: .45rem .6rem; text-align: left; border-bottom: 1px solid
         color-mix(in srgb, currentColor 20%, transparent); }
th { cursor: pointer; user-select: none; white-space: nowrap; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.wilson { opacity: .65; font-size: .8em; }
footer { opacity: .7; font-size: .85rem; margin-top: 3rem; }
"""


def build(config: dict, out_root: Path | None = None) -> Path:
    out = out_root or (ROOT / "site")
    out.mkdir(parents=True, exist_ok=True)
    dv = config["dataset_version"]

    rows = []
    boards = {}
    for split in ("public", "private"):
        p = ROOT / "results" / dv / split / "summary.json"
        if p.exists():
            boards[split] = _load(p)
    if "public" not in boards:
        raise SystemExit("no public results — run the benchmark first")
    pub = boards["public"]["tools"]

    best = max(pub.items(), key=lambda kv: kv[1]["documents"]["rate"])
    bid, bs = best
    headline = (f"{bs['display_name']} leads with "
                f"{bs['documents']['rate']:.1%} document exact-match "
                f"(n={bs['documents']['count']}, Wilson95 "
                f"{bs['documents']['wilson95'][0]:.0%}–"
                f"{bs['documents']['wilson95'][1]:.0%}) at "
                f"${bs['cost_per_correct_doc_usd']:.4f} per fully-correct "
                f"document on the public split.")

    for tid, s in sorted(pub.items(), key=lambda kv: -kv[1]["documents"]["rate"]):
        em = s["documents"]
        prv = boards.get("private", {}).get("tools", {}).get(tid)
        prv_rate = (f"{prv['documents']['rate']:.1%}" if prv else "—")
        rows.append(f"""
<tr><td>{s['display_name']}<div class="wilson">{tid} · {s['tool_version']}</div></td>
<td class="num">{em['rate']:.1%}<div class="wilson">{em['successes']}/{em['count']} · 95% CI {em['wilson95'][0]:.0%}–{em['wilson95'][1]:.0%}</div></td>
<td class="num">{prv_rate}</td>
<td class="num">{s['field_accuracy']['rate']:.1%}</td>
<td class="num">{s['cost_per_correct_doc_usd'] if s['cost_per_correct_doc_usd'] is not None else '—'}</td>
<td class="num">{s['latency_ms']['p50']:.1f}s</td></tr>""")

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{config.get('project_name', 'agentbench')} — invoice extraction leaderboard</title>
<style>{CSS}</style></head><body>
<h1>Global Invoice Extraction Benchmark</h1>
<p class="sub">Neutral, ground-truth-scored — 104 synthetic invoices per split across
13 countries, 4 degradation levels, 7 scripts, 3 calendars. Dataset {dv}.</p>
<p><strong>Headline:</strong> {headline}</p>
<table id="board">
<thead><tr><th>Tool</th><th class="num">Exact-match (public)</th>
<th class="num">Private</th><th class="num">Field acc</th>
<th class="num">$/correct doc</th><th class="num">p50</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p>Full breakdowns by country, degradation level, calendar and more in the
<a href="/api/v1/categories/invoices/index.json">agent API</a> ·
methodology and the exact LLM prompt: /methodology (M3).</p>
<footer>Methodology, generator code and public dataset are open (code MIT,
data CC BY 4.0). Every rate carries a 95% Wilson interval and n. Tools tested
with identical documents; LLMs share one prompt; no vendor paid for
placement.</footer>
<script>
// column sort on header click (scaffold nicety)
document.querySelectorAll('#board th').forEach((th, i) => {{
  th.onclick = () => {{
    const tbody = document.querySelector('#board tbody');
    [...tbody.rows].sort((a, b) => {{
      const x = a.cells[i].textContent, y = b.cells[i].textContent;
      const nx = parseFloat(x.replace(/[^0-9.]/g, '')), ny = parseFloat(y.replace(/[^0-9.]/g, ''));
      return (isNaN(nx) || isNaN(ny)) ? x.localeCompare(y) : ny - nx;
    }}).forEach(r => tbody.appendChild(r));
  }};
}});
</script></body></html>"""
    (out / "index.html").write_text(html, encoding="utf-8")
    print(f"site -> {out / 'index.html'}")
    return out / "index.html"


if __name__ == "__main__":
    from core.config import load_config
    build(load_config())
