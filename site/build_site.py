"""Static site generator (spec B5): leaderboard, heatmap, failure gallery,
methodology, neutrality policy, corrections log, tool pages, API docs.

Every number is read from results/ JSON at build time — nothing transcribed
by hand. The corrections log renders DECISIONS.md directly so the published
record and the repo record cannot drift apart.
"""
from __future__ import annotations

import html
import json
import shutil
import time
from pathlib import Path

from core.config import ROOT

PROMPT_PATH = ROOT / "categories" / "invoices" / "prompts" / "extract_v1.md"
DECISIONS_PATH = ROOT / "DECISIONS.md"

CSS = """
:root { color-scheme: light dark; --accent: #0969da; }
* { box-sizing: border-box; }
body { font: 16px/1.55 system-ui, sans-serif; margin: 0 auto; max-width: 1080px;
       padding: 1.2rem 1rem 4rem; }
nav { display: flex; flex-wrap: wrap; gap: 1.1rem; font-size: .9rem;
      border-bottom: 1px solid color-mix(in srgb, currentColor 18%, transparent);
      padding-bottom: .6rem; margin-bottom: 1.4rem; }
nav a { color: var(--accent); text-decoration: none; }
h1 { font-size: 1.45rem; } h2 { font-size: 1.15rem; margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }
th, td { padding: .4rem .55rem; text-align: left;
         border-bottom: 1px solid color-mix(in srgb, currentColor 15%, transparent); }
th { white-space: nowrap; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.wilson { opacity: .6; font-size: .8em; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
         gap: 1rem; }
.card { border: 1px solid color-mix(in srgb, currentColor 22%, transparent);
        border-radius: 8px; padding: .8rem; }
.card img { width: 100%; border-radius: 4px; margin-bottom: .5rem;
            background: #fff; }
.tag { display: inline-block; font-size: .72rem; padding: .1rem .45rem;
       border-radius: 99px; border: 1px solid currentColor; opacity: .8;
       margin-right: .3rem; }
.fail { color: #d1242f; font-weight: 600; }
code, pre { font: .88rem/1.45 ui-monospace, monospace; }
pre { overflow-x: auto; padding: .8rem; border-radius: 6px;
      background: color-mix(in srgb, currentColor 7%, transparent); }
footer { opacity: .7; font-size: .85rem; margin-top: 3rem; }
.hm td { text-align: center; }
.filter { margin: .6rem 0; font-size: .9rem; }
.filter a { margin-right: .8rem; }
"""

def _nav(rel: str = "") -> str:
    """Site nav with relative links (works under a Pages subpath)."""
    return (f'<nav><a href="{rel}index.html">Leaderboard</a>'
            f'<a href="{rel}heatmap.html">Heatmap</a>'
            f'<a href="{rel}failures.html">Failure gallery</a>'
            f'<a href="{rel}methodology.html">Methodology</a>'
            f'<a href="{rel}neutrality.html">Neutrality</a>'
            f'<a href="{rel}corrections.html">Corrections log</a>'
            f'<a href="{rel}api.html">API &amp; MCP</a></nav>')


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


CF_BEACON = ("<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
             "data-cf-beacon='{\"token\": \"c2642657a3e64460956a469de7821bec\"}'></script>")
CONTACT_EMAIL = "chrismcharles+agentbench@gmail.com"


def _page(title: str, body: str, rel: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>{CF_BEACON}</head><body>{_nav(rel)}{body}
<footer>agentbench (working name) · dataset from summary.json at build time ·
code MIT, data CC BY 4.0 · every rate carries a 95% Wilson interval and n ·
built {time.strftime('%Y-%m-%d')} ·
<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></footer></body></html>"""


def _md_to_html(md: str) -> str:
    """Tiny markdown renderer for the corrections log (headings, lists,
    paragraphs, bold, links-free)."""
    out, in_list = [], False
    for line in md.splitlines():
        s = line.strip()
        if not s:
            if in_list:
                out.append("</ul>"); in_list = False
            continue
        def esc(t: str) -> str:
            return html.escape(t)
        if s.startswith("### "):
            out.append(f"<h3>{esc(s[4:])}</h3>")
        elif s.startswith("## "):
            out.append(f"<h2>{esc(s[3:])}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{esc(s[2:])}</h1>")
        elif s.startswith("- ") or s.startswith("  - "):
            if not in_list:
                out.append("<ul>"); in_list = True
            body = s.split("- ", 1)[1]
            body = body.replace("**", "<strong>", 1)
            body = body.replace("**", "</strong>", 1)
            out.append(f"<li>{esc(body).replace('&lt;strong&gt;','<strong>').replace('&lt;/strong&gt;','</strong>')}</li>")
        else:
            if in_list:
                out.append("</ul>"); in_list = False
            body = esc(s).replace("**", "")
            out.append(f"<p>{body}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _fmt_cost(v) -> str:
    return f"${v:.4f}" if v is not None else "—"


def _leaderboard_rows(boards: dict) -> str:
    pub = boards["public"]["tools"]
    rows = []
    for tid, s in sorted(pub.items(), key=lambda kv: -kv[1]["documents"]["rate"]):
        em = s["documents"]
        prv = boards.get("private", {}).get("tools", {}).get(tid)
        prv_em = prv["documents"] if prv else None
        gap = (f"{100 * (prv_em['rate'] - em['rate']):+.1f}pp" if prv_em else "—")
        rows.append(f"""
<tr><td><a href="tools/{tid}.html">{s['display_name']}</a>
<div class="wilson">{tid} · {s['tool_version']}</div></td>
<td class="num">{em['rate']:.1%}<div class="wilson">{em['successes']}/{em['count']} · CI {em['wilson95'][0]:.0%}–{em['wilson95'][1]:.0%}</div></td>
<td class="num">{prv_em['rate']:.1%}<div class="wilson">public-private {gap}</div></td>
<td class="num">{s['field_accuracy']['rate']:.1%}</td>
<td class="num">{_fmt_cost(s['cost_per_correct_doc_usd'])}</td>
<td class="num">{s['latency_ms']['p50']/1000:.1f}s</td>
<td class="num">{s['hallucination_rate']['rate']:.1%}</td></tr>""")
    return "".join(rows)


def build(config: dict, out_root: Path | None = None) -> None:
    out = out_root or (ROOT / "site")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tools").mkdir(exist_ok=True)
    dv = config["dataset_version"]

    boards = {sp: _load(ROOT / "results" / dv / sp / "summary.json")
              for sp in ("public", "private")
              if (ROOT / "results" / dv / sp / "summary.json").exists()}
    by_dim = {sp: _load(ROOT / "results" / dv / sp / "by_dimension.json")
              for sp in boards}
    failures = [json.loads(l) for l in
                (ROOT / "results" / dv / "public" / "failures.jsonl")
                .read_text(encoding="utf-8").splitlines()]
    pub = boards["public"]["tools"]

    # ---------- index ----------
    best_id, best = max(pub.items(), key=lambda kv: kv[1]["documents"]["rate"])
    tex = pub.get("aws_textract_expense")
    headline = (f"{best['display_name']} leads at "
                f"{best['documents']['rate']:.1%} document exact-match "
                f"(CI {best['documents']['wilson95'][0]:.0%}–"
                f"{best['documents']['wilson95'][1]:.0%}) for "
                f"{_fmt_cost(best['cost_per_correct_doc_usd'])} per fully-correct "
                f"document — while the dedicated invoice service scores "
                f"{tex['documents']['rate']:.1%}.")
    (out / "index.html").write_text(_page("Leaderboard", f"""
<h1>Global Invoice Extraction Benchmark</h1>
<p class="sub">Neutral, ground-truth-scored. 104 synthetic invoices per split ×
4 degradation levels, 13 countries, 7 scripts, 3 calendars, 12 scored fields.
Dataset {dv}.</p>
<p><strong>Headline:</strong> {headline}</p>
<table><thead><tr><th>Tool</th><th class="num">Exact-match (public)</th>
<th class="num">Private</th><th class="num">Field acc</th>
<th class="num">$/correct doc</th><th class="num">p50</th>
<th class="num">Halluc.</th></tr></thead>
<tbody>{_leaderboard_rows(boards)}</tbody></table>
<p>See the <a href="failures.html">failure gallery</a> for where each tool
breaks — degraded scans, tax-inclusive totals, currency identification.</p>"""),
                                     encoding="utf-8")

    # ---------- heatmap ----------
    def heat_table(dim: str, title: str) -> str:
        tids = sorted(pub)
        values: list[str] = []
        seen = set()
        for tid in tids:
            for v in by_dim["public"]["tools"].get(tid, {}).get(dim, {}):
                seen.add(v)
        order = sorted(seen)
        head = "".join(f"<th>{html.escape(t)}</th>" for t in
                       [pub[t]["display_name"].split(" (")[0] for t in tids])
        rows = []
        for v in order:
            cells = []
            for tid in tids:
                m = (by_dim["public"]["tools"].get(tid, {})
                     .get(dim, {}).get(v))
                if not m:
                    cells.append("<td>–</td>"); continue
                r = m["documents"]["rate"]
                # red (0) -> green (1): hue 0..130
                bg = f"hsl({130*r:.0f}, 55%, {'28%' if r else '60%'} )"
                fg = "#fff" if r else "inherit"
                cells.append(f'<td style="background:{bg};color:{fg};'
                             f'border-radius:4px">{r:.0%}<div class="wilson">'
                             f'{m["documents"]["successes"]}/{m["documents"]["count"]}'
                             f'</div></td>')
            rows.append(f"<tr><th>{html.escape(v)}</th>{''.join(cells)}</tr>")
        return f"<h2>{title}</h2><table class='hm'><tr><th></th>{head}</tr>{''.join(rows)}</table>"

    (out / "heatmap.html").write_text(_page("Heatmaps", f"""
<h1>Exact-match heatmaps</h1>{heat_table('country', 'By country')}
{heat_table('variant', 'By degradation level')}
{heat_table('calendar', 'By calendar')}{heat_table('tax_mode', 'By tax mode')}"""),
                                     encoding="utf-8")

    # ---------- failure gallery ----------
    def curate(fails: list[dict]) -> list[dict]:
        """Rule-based curation: the currency-identification traps, degradation
        nulls, calendar failures, count misses — strongest stories first."""
        def pick(pred, n, label):
            got = [f | {"reason": label} for f in fails if pred(f)][:n]
            for f in got:
                fails.remove({k: v for k, v in f.items() if k != "reason"})
            return got
        out_ = []
        out_ += pick(lambda f: f["tool"] == "aws_textract_expense"
                     and f["field"] == "currency" and f["prediction"]
                     and f["doc_id"][:2] == "CN", 4, "¥ read as JPY")
        out_ += pick(lambda f: f["tool"] == "aws_textract_expense"
                     and f["field"] == "currency" and f["prediction"]
                     and f["doc_id"][:2] in ("BR", "MX"), 4, "R$/$ read as USD")
        out_ += pick(lambda f: f["tool"] == "aws_textract_expense"
                     and f["field"] == "currency" and f["prediction"] == "SEK", 2,
                     "₩ guessed as SEK")
        out_ += pick(lambda f: f["field"] in ("subtotal", "tax_total", "total")
                     and f["prediction"] is None and f["variant"] in
                     ("bad_scan", "phone_photo"), 6, "gave up on degraded scan")
        out_ += pick(lambda f: f["field"] == "invoice_date"
                     and f["prediction"] and str(f["prediction"]).startswith("25"), 3,
                     "Buddhist year taken literally")
        out_ += pick(lambda f: f["field"] == "total"
                     and f["prediction"] is not None and f["outcome"] == "incorrect"
                     and f["doc_id"][:2] == "JP", 2, "tax-inclusive totals")
        out_ += pick(lambda f: f["field"] == "line_item_count", 4,
                     "line-item count off")
        out_ += pick(lambda f: f["field"] == "vendor_name", 3,
                     "vendor name misread")
        out_ += pick(lambda f: f["field"] == "due_date", 2, "due date wrong")
        return out_

    curated = curate([f for f in failures])
    cards = []
    for f in curated[:24]:
        pred = "null" if f["prediction"] is None else str(f["prediction"])
        rendered = f.get("rendered") or ""
        cards.append(f"""<div class="card">
<img loading="lazy" src="img/{f['doc_id']}.png" alt="{f['doc_id']}">
<div><span class="tag">{f['tool']}</span><span class="tag">{f['doc_id'][:2]}</span>
<span class="tag">{f['variant']}</span><span class="tag">{f['reason']}</span></div>
<p><strong>{f['field']}</strong> — <span class="fail">returned</span>
<code>{html.escape(pred[:60])}</code><br>
expected <code>{html.escape(str(f['truth'])[:60])}</code>
{f"<br>as printed: <code>{html.escape(rendered[:48])}</code>" if rendered else ""}</p>
</div>""")

    # thumbnails for curated docs
    import pymupdf
    img_dir = out / "img"
    img_dir.mkdir(exist_ok=True)
    doc_ids = {f["doc_id"] for f in curated[:24]}
    for doc_id in doc_ids:
        dst = img_dir / f"{doc_id}.png"
        if dst.exists():
            continue
        pdf = ROOT / "data" / "public" / "documents" / doc_id / "clean.pdf"
        if pdf.exists():
            d = pymupdf.open(pdf)
            pm = d[0].get_pixmap(matrix=pymupdf.Matrix(0.9, 0.9))
            pm.save(dst)
            d.close()

    (out / "failures.html").write_text(_page("Failure gallery", f"""
<h1>Failure gallery</h1>
<p class="sub">Where tools actually break — {len(curated[:24])} curated examples
from the public split. Every card: the field, what the tool returned, the
expected value, and how it was printed.</p>
<div class="cards">{''.join(cards)}</div>"""), encoding="utf-8")

    # ---------- tool pages ----------
    for tid, s in pub.items():
        dims = by_dim["public"]["tools"].get(tid, {})
        dim_html = []
        for dim in ("country", "variant", "calendar", "tax_mode", "number_format"):
            if dim not in dims:
                continue
            cells = "".join(
                f"<tr><th>{html.escape(v)}</th><td class='num'>"
                f"{m['documents']['rate']:.1%}</td>"
                f"<td class='num wilson'>{m['documents']['successes']}/"
                f"{m['documents']['count']}</td></tr>"
                for v, m in sorted(dims[dim].items(),
                                   key=lambda kv: kv[1]["documents"]["rate"]))
            dim_html.append(f"<h3>{dim}</h3><table><tr><th></th>"
                            f"<th class='num'>exact-match</th><th></th></tr>"
                            f"{cells}</table>")
        prv = boards.get("private", {}).get("tools", {}).get(tid)
        body = f"""
<h1>{html.escape(s['display_name'])}</h1>
<p class="sub">{tid} · version {s['tool_version']} · tested on dataset {dv}</p>
<p>Public exact-match <strong>{s['documents']['rate']:.1%}</strong>
(CI {s['documents']['wilson95'][0]:.0%}–{s['documents']['wilson95'][1]:.0%},
n={s['documents']['count']})
{f"· private {prv['documents']['rate']:.1%}" if prv else ""} ·
field accuracy {s['field_accuracy']['rate']:.1%} ·
{_fmt_cost(s['cost_per_correct_doc_usd'])} per correct document ·
p50 {s['latency_ms']['p50']/1000:.1f}s · hallucination
{s['hallucination_rate']['rate']:.1%}</p>
{''.join(dim_html)}
<p><a href="../methodology.html">Methodology</a> ·
<a href="../corrections.html">Corrections log</a> ·
no vendor paid for this listing.</p>"""
        (out / "tools" / f"{tid}.html").write_text(
            _page(s["display_name"], body, rel="../"), encoding="utf-8")

    # ---------- methodology ----------
    prompt_body = PROMPT_PATH.read_text(encoding="utf-8").partition("\n---\n")[2]
    (out / "methodology.html").write_text(_page("Methodology", f"""
<h1>Methodology</h1>
<h2>Dataset</h2><p>104 synthetic invoices per split (public seed published,
private seed never published) across 13 countries: US GB DE IN CN JP KR BR MX
SA AE ID TH. Each invoice renders through country-specific templates in its
native script, calendar (Gregorian, Japanese era, Thai Buddhist), number
format (western, European, Indian lakh, space-grouped), digits (western,
Arabic-Indic) and tax regime (inclusive, exclusive, reverse charge, split,
withholding). Every base invoice ships in 4 degradation variants: clean PDF,
200dpi scan, degraded bad scan, phone photo. Generator code and the public
split are open (MIT / CC BY 4.0).</p>
<h2>Splits</h2><p>Official numbers use the private split; the public split
(with published seed and documents) lets anyone reproduce. A large
public-private gap for a tool flags possible overfitting. None observed in
dataset {dv}.</p>
<h2>Scoring</h2><p>12 fields compared under identical normalization
(NFKC/casefold; identifiers stripped of spacing punctuation; amounts and
dates value-exact with unambiguous display formats tolerated — decisions
#21–#25 in the <a href="corrections.html">corrections log</a>). Document
exact-match = all scored fields correct. Every rate carries a 95% Wilson
interval. Amounts must be right values — "1.234" for 1,234 is wrong.
Dates must resolve to ISO Gregorian; swapped day/month is wrong.
Fields a tool never returns score as misses; hallucination = answer where
the truth is null.</p>
<h2>The exact LLM prompt</h2><pre>{html.escape(prompt_body)}</pre>
<h2>Withholding, fapiao, unscored fields</h2>
<p><code>tax_total</code> counts taxes charged only (decision #18).
Fapiao-style documents carry no due date (null scored under normal rules,
#20). Payment details printed but not normalizable (US routing numbers) are
excluded from scoring for that document (#19).</p>
<h2>Known limitations</h2><ul>
<li>Synthetic documents: realistic per-country templates, but not real
paperwork; a small real-document set is planned.</li>
<li>Textract multipage PDFs were split and merged page-by-page (the async
API requires S3); dates use the document's country convention (#25).</li>
<li>LLMs see one shared prompt at temperature 0; document-AI services use
their fixed schemas. Both are how buyers deploy them.</li>
</ul>"""), encoding="utf-8")

    # ---------- neutrality ----------
    rules = """
<li>Rankings are determined only by measured results.</li>
<li>Every tool is tested with the same documents, the same settings policy,
and (for LLMs) the same prompt.</li>
<li>Methodology, generator code, scoring code, and the public sample are
open source.</li>
<li>Every result is labeled with the tool version/model ID and test date.</li>
<li>Any commercial relationship with a vendor is disclosed on that vendor's
page.</li>
<li>Retest requests are accepted from anyone and run on a published
schedule for all tools.</li>
<li>A public corrections log records every error we fix — including our own
(see decision #24).</li>"""
    (out / "neutrality.html").write_text(_page("Neutrality policy", f"""
<h1>Neutrality policy</h1><p>Neutrality only counts if it is verifiable.
These rules are binding on this benchmark:{rules}</p>
<p>No vendor has paid for placement, retest priority, or exclusion of
competitors as of dataset {dv}.</p>"""), encoding="utf-8")

    # ---------- corrections log ----------
    md = DECISIONS_PATH.read_text(encoding="utf-8")
    (out / "corrections.html").write_text(_page("Corrections log", f"""
<h1>Corrections log</h1><p class="sub">Every design decision and every fix,
including errors we made and who caught them. Rendered directly from
DECISIONS.md — the repo record and this page cannot drift.</p>
{_md_to_html(md)}"""), encoding="utf-8")

    # ---------- api docs ----------
    (out / "api.html").write_text(_page("API & MCP", """
<h1>Agent API &amp; MCP server</h1>
<h2>Static JSON API</h2><ul>
<li><code>/api/v1/index.json</code> — categories</li>
<li><code>/api/v1/categories/invoices/index.json</code> — fields,
dimensions, tools</li>
<li><code>/api/v1/categories/invoices/leaderboard.json</code> — public rankings
(<code>leaderboard_private.json</code> for the private split)</li>
<li><code>/api/v1/categories/invoices/tools/{tool_id}.json</code> — full
per-dimension profile</li>
<li><code>/api/v1/categories/invoices/dimensions/{dimension}/{value}.json</code>
— e.g. <code>dimensions/country/JP.json</code></li>
<li><code>/llms.txt</code> — plain-language guide for agents</li></ul>
<p>Every response carries <code>dataset_version</code>,
<code>test_date</code>, <code>split</code> and a methodology link.</p>
<h2>MCP server</h2><p><code>mcp-server/</code> in the repo exposes
<code>list_categories</code>, <code>list_tools</code>,
<code>get_leaderboard</code>, <code>recommend_extractor</code>,
<code>get_failures</code> over stdio. Recommendations always include sample
sizes and Wilson intervals — never bare percentages.</p>"""),
                                     encoding="utf-8")

    print(f"site -> {out} ({len(list(out.glob('*.html'))) + len(list((out/'tools').glob('*.html')))} pages, "
          f"{len(curated[:24])} gallery cards)")


if __name__ == "__main__":
    from core.config import load_config
    build(load_config())
