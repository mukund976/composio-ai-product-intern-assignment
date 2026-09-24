#!/usr/bin/env python3
"""
pipeline/build_site.py — renders the single self-contained case-study page.

Reads:  data/final_research.json, reports/analysis.json, score reports
Writes: site/index.html   (zero external assets — inline CSS/JS/data)

Design notes: this is the PRODUCT case study view. Deep verification mechanics
(loops, correction ledgers, probe logs) live in the repo (data/verification_log.json,
data/corrections.json, reports/) and are intentionally not rendered on the page.

  python3 pipeline/build_site.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def load(p):
    return json.loads((ROOT / p).read_text())


def esc(s):
    return html.escape(str(s or ""))


AUTH_LABEL = {"OAuth2": "OAuth2", "API key": "API key", "Basic": "Basic", "Token": "Token",
              "JWT": "JWT", "JWT key-pair": "JWT KP", "Bot token": "Bot tok", "HMAC": "HMAC",
              "OAuth1": "OAuth1", "Digest": "Digest", "None": "None"}
ACC_LABEL = {"self-serve-free": "Free self-serve", "self-serve-paid-or-trial": "Paid / trial",
             "approval-gated": "Approval gate", "enterprise-gated": "Enterprise gate",
             "no-public-api": "No API"}
VER_LABEL = {"build-now": "Build now", "build-with-friction": "Build w/ friction", "blocked": "Blocked"}


def auth_chips(auths):
    out = []
    for a in auths:
        cls = {"OAuth2": "a-oauth", "API key": "a-key", "Token": "a-key", "Basic": "a-basic",
               "JWT": "a-jwt", "JWT key-pair": "a-jwt", "HMAC": "a-hmac", "Bot token": "a-bot",
               "OAuth1": "a-oauth", "Digest": "a-basic", "None": "a-none"}.get(a, "a-none")
        out.append(f'<span class="chip {cls}">{esc(AUTH_LABEL.get(a, a))}</span>')
    return " ".join(out)


def verdict_chip(v):
    cls = {"build-now": "v-now", "build-with-friction": "v-friction", "blocked": "v-blocked"}[v]
    return f'<span class="chip {cls}">{esc(VER_LABEL[v])}</span>'


def acc_chip(a):
    cls = {"self-serve-free": "acc-free", "self-serve-paid-or-trial": "acc-paid",
           "approval-gated": "acc-appr", "enterprise-gated": "acc-ent",
           "no-public-api": "acc-no"}[a]
    return f'<span class="chip {cls}">{esc(ACC_LABEL[a])}</span>'


def mcp_chip(m):
    cls = {"official": "m-off", "community": "m-com", "none-found": "m-none"}[m]
    label = {"official": "Official MCP", "community": "Community MCP", "none-found": "No MCP"}[m]
    return f'<span class="chip {cls}">{label}</span>'


def build_rows(recs):
    rows = []
    for r in recs:
        ev = " ".join(f'<a href="{esc(u)}" target="_blank" rel="noopener">[{i+1}]</a>'
                      for i, u in enumerate(r.get("evidence", [])))
        ev_list = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></li>'
                          for u in r.get("evidence", []))
        detail = (f'<details><summary>detail</summary>'
                  f'<p><b>Auth:</b> {esc(r.get("auth_detail"))}</p>'
                  f'<p><b>Access:</b> {esc(r.get("access_detail"))}</p>'
                  f'<p><b>MCP:</b> {esc(r.get("mcp_detail") or "—")}</p>'
                  + (f'<p><b>Blocker:</b> {esc(r.get("blocker"))}</p>' if r.get("blocker") else "")
                  + f'<p><b>Confidence:</b> {esc(r.get("confidence"))} · <b>API:</b> {esc(", ".join(r.get("api_surface", [])))} ({esc(r.get("api_breadth"))})</p>'
                  f'<ul class="ev">{ev_list}</ul></details>')
        rows.append(
            f'<tr data-cat="{esc(r["category"])}" data-acc="{esc(r["access"])}" data-ver="{esc(r["verdict"])}" '
            f'data-mcp="{esc(r["mcp"])}" data-auth="{esc(",".join(r.get("auth", [])))}" '
            f'data-name="{esc(r["name"].lower())}">'
            f'<td class="num">{r["id"]}</td>'
            f'<td class="app">{esc(r["name"])}<div class="one">{esc(r["one_liner"])}</div></td>'
            f'<td>{esc(r["category"])}</td>'
            f'<td>{auth_chips(r.get("auth", []))}</td>'
            f'<td>{acc_chip(r["access"])}</td>'
            f'<td class="api">{esc(" + ".join(r.get("api_surface", [])))}<span class="bw"> · {esc(r.get("api_breadth"))}</span></td>'
            f'<td>{mcp_chip(r["mcp"])}</td>'
            f'<td>{verdict_chip(r["verdict"])}</td>'
            f'<td class="ev-td">{ev} {detail}</td></tr>')
    return "\n".join(rows)


def access_bar(counter, order, colors):
    total = sum(counter.values())
    segs = []
    for k in order:
        v = counter.get(k, 0)
        if not v:
            continue
        pct = 100 * v / total
        segs.append(f'<div class="seg" style="width:{pct:.1f}%;background:{colors[k]}" '
                    f'title="{esc(ACC_LABEL[k])}: {v}">{v}</div>')
    legend = " ".join(f'<span class="lg"><i style="background:{colors[k]}"></i>{esc(ACC_LABEL[k])} <b>{counter.get(k,0)}</b></span>' for k in order)
    return f'<div class="bar">{"".join(segs)}</div><div class="legend">{legend}</div>'


def main():
    fin = load("data/final_research.json")
    an = load("reports/analysis.json")
    s1 = load("reports/pass1_research_score.json")
    s2 = load("reports/final_research_score.json")
    recs = fin["records"]

    cats = an["category_order"]
    acc_order = ["self-serve-free", "self-serve-paid-or-trial", "approval-gated", "enterprise-gated", "no-public-api"]
    acc_colors = {"self-serve-free": "#22c55e", "self-serve-paid-or-trial": "#84cc16",
                  "approval-gated": "#f59e0b", "enterprise-gated": "#ef4444", "no-public-api": "#6b7280"}

    heat_rows = []
    for c in cats:
        ac = an["access_by_category"][c]
        vc = an["verdict_by_category"][c]
        n = sum(ac.values())
        free = ac.get("self-serve-free", 0)
        paid = ac.get("self-serve-paid-or-trial", 0)
        gate = ac.get("approval-gated", 0) + ac.get("enterprise-gated", 0) + ac.get("no-public-api", 0)
        now = vc.get("build-now", 0)
        heat_rows.append(
            f'<tr><td>{esc(c)}</td><td class="num">{n}</td>'
            f'<td><div class="minibar"><span style="width:{100*free/n:.0f}%;background:#22c55e"></span>'
            f'<span style="width:{100*paid/n:.0f}%;background:#84cc16"></span>'
            f'<span style="width:{100*gate/n:.0f}%;background:#ef4444"></span></div></td>'
            f'<td class="num">{now}/{n}</td></tr>')

    def short_list(items, limit, extra=None):
        li = []
        for r in items[:limit]:
            e = f' <span class="dim">— {esc(extra(r))}</span>' if extra else ""
            li.append(f'<li><b>{esc(r["name"])}</b>{e}</li>')
        more = f'<li class="dim">+{len(items)-limit} more in the dataset below</li>' if len(items) > limit else ""
        return "".join(li) + more

    easy, outreach, blocked = an["easy_wins"], an["needs_outreach"], an["blocked"]

    miss_rows = "".join(
        f'<tr><td class="num">{m["id"]}</td><td>{esc(m["name"])}</td><td>{esc(m["field"])}</td>'
        f'<td class="mono">{esc(json.dumps(m["predicted"]))}</td><td class="mono">{esc(json.dumps(m["gold"]))}</td></tr>'
        for m in s1["misses"])

    rows = build_rows(recs)
    dataset_json = json.dumps({"generated_from": "data/final_research.json", "apps": recs}, ensure_ascii=False)
    dataset_json = dataset_json.replace("</", "<\\/")
    cat_options = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cats)

    repl = {
        "__ROWS__": rows,
        "__CAT_OPTIONS__": cat_options,
        "__DATASET_JSON__": dataset_json,
        "__N__": str(an["n"]),
        "__SS_PCT__": str(an["access_pct_selfserveable"]),
        "__FREE__": str(an["access_counts"].get("self-serve-free", 0)),
        "__PAID__": str(an["access_counts"].get("self-serve-paid-or-trial", 0)),
        "__APPROVAL__": str(an["access_counts"].get("approval-gated", 0)),
        "__ENTERPRISE__": str(an["access_counts"].get("enterprise-gated", 0)),
        "__NOAPI__": str(an["access_counts"].get("no-public-api", 0)),
        "__BUILD_NOW__": str(an["verdict_counts"].get("build-now", 0)),
        "__FRICTION__": str(an["verdict_counts"].get("build-with-friction", 0)),
        "__BLOCKED__": str(an["verdict_counts"].get("blocked", 0)),
        "__STATIC__": str(an["auth_family_counts"].get("static-key", 0)),
        "__OAUTH__": str(an["auth_family_counts"].get("oauth2", 0)),
        "__HYBRID__": str(an["hybrid_oauth_plus_static"]),
        "__AUTH_BASIC_N__": str(an["auth_family_counts"].get("basic", 0)),
        "__AUTH_JWT_N__": str(an["auth_family_counts"].get("jwt", 0)),
        "__AUTH_HMAC_N__": str(an["auth_family_counts"].get("hmac", 0)),
        "__AUTH_BOT_N__": str(an["auth_family_counts"].get("bot token", 0)),
        "__MCP_OFF__": str(an["mcp_counts"].get("official", 0)),
        "__MCP_COM__": str(an["mcp_counts"].get("community", 0)),
        "__EASY_N__": str(len(easy)),
        "__OUTREACH_N__": str(len(outreach)),
        "__HEAT_ROWS__": "".join(heat_rows),
        "__ACCESS_BAR__": access_bar(an["access_counts"], acc_order, acc_colors),
        "__BLOCKER_BARS__": "".join(
            f'<div class="brow"><span class="blab">{esc(k)}</span><div class="btrack"><div class="bfill" style="width:{28*v}%"></div></div><b>{v}</b></div>'
            for k, v in an["blocker_classes"].items()),
        "__EASY_LIST__": short_list(easy, 8),
        "__OUTREACH_LIST__": short_list(outreach, 8, extra=lambda r: r.get("blocker", "")[:70]),
        "__BLOCKED_LIST__": short_list(blocked, 3, extra=lambda r: r.get("blocker", "")[:80]),
        "__MISS_ROWS__": miss_rows,
        "__S1_PCT__": str(s1["accuracy_pct"]),
        "__S1_C__": f'{s1["correct"]}/{s1["checks"]}',
        "__S2_PCT__": str(s2["accuracy_pct"]),
        "__S2_C__": f'{s2["correct"]}/{s2["checks"]}',
        "__BLOCKER_TOP__": " / ".join(list(an["blocker_classes"].keys())[:2]),
    }
    html_doc = HTML_TEMPLATE
    for k, v in repl.items():
        html_doc = html_doc.replace(k, v)

    SITE.mkdir(exist_ok=True)
    out = SITE / "index.html"
    out.write_text(html_doc, encoding="utf-8")
    print(f"✓ {out} ({out.stat().st_size/1024:.1f} KB, self-contained)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>100 Apps, 100 Toolkits? — Composio take-home case study</title>
<meta name="description" content="Agent-researched, human-verified analysis of 100 apps for AI agent toolkits: auth, access gating, API surface, MCP, buildability. 96.9% to 100% agreement on 195 audited checks.">
<style>
:root{--bg:#0b0d14;--card:#12151f;--card2:#171b28;--ink:#e8eaf2;--dim:#98a0b3;--line:#242a3a;
--vio:#8b7cf8;--vio2:#6c5ce7;--grn:#22c55e;--lim:#84cc16;--amb:#f59e0b;--red:#ef4444;--blu:#38bdf8;}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:linear-gradient(180deg,#0b0d14 0%,#0e1018 100%);color:var(--ink);
 font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding-bottom:80px}
a{color:var(--blu);text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:1140px;margin:0 auto;padding:0 22px}
header.hero{padding:46px 0 24px;border-bottom:1px solid var(--line);background:
 radial-gradient(900px 320px at 82% -60px,rgba(139,124,248,.20),transparent 70%)}
.kicker{color:var(--vio);font-weight:700;letter-spacing:.14em;font-size:12px;text-transform:uppercase}
h1{font-size:clamp(25px,3.6vw,36px);line-height:1.12;margin:10px 0 10px;font-weight:800}
h1 .grad{background:linear-gradient(92deg,#a78bfa,#38bdf8);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--dim);max-width:720px;font-size:15px}
.submit{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:16px 0 0;padding:12px 14px;background:var(--card);border:1px solid rgba(139,124,248,.4);border-radius:12px}
.btn{display:inline-block;background:linear-gradient(92deg,var(--vio2),var(--vio));color:#fff;font-weight:700;font-size:13.5px;padding:9px 15px;border-radius:10px}
.btn:hover{text-decoration:none;filter:brightness(1.1)}
.tldr{margin:14px 0 0;padding:14px 16px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--grn);border-radius:12px}
.tldr>b{font-size:12.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--grn)}
.meta-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.meta-chips span{background:var(--card2);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:12.5px;color:var(--dim)}
.covmap{margin-top:10px;font-size:12px;color:var(--dim)}
.covmap a{color:var(--dim);text-decoration:underline dotted}
nav.sticky{position:sticky;top:0;z-index:50;background:rgba(11,13,20,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
nav.sticky .wrap{display:flex;gap:18px;padding:11px 22px;overflow:auto}
nav.sticky a{color:var(--dim);font-size:13.5px;white-space:nowrap}
nav.sticky a:hover{color:var(--ink);text-decoration:none}
section{padding:40px 0 6px}
h2{font-size:23px;margin:6px 0 4px;font-weight:800}
h2 .n{color:var(--vio);font-family:ui-monospace,monospace;font-size:15px;vertical-align:middle;margin-right:8px}
h3{font-size:15.5px;margin:18px 0 8px}
p.lede{color:var(--dim);max-width:820px;margin-bottom:16px;font-size:14.5px}
.grid{display:grid;gap:13px}
.g3{grid-template-columns:repeat(auto-fit,minmax(225px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(310px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.card h4{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.08em;margin-bottom:7px}
.big{font-size:31px;font-weight:800;line-height:1.1}
.big.vio{color:var(--vio)} .big.grn{color:var(--grn)} .big.amb{color:var(--amb)} .big.blu{color:var(--blu)}
.card p{color:var(--dim);font-size:13px;margin-top:6px}
.pattern{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--vio);border-radius:12px;padding:14px 16px}
.pattern b.t{display:block;font-size:14.5px;margin-bottom:5px}
.pattern p{color:var(--dim);font-size:13.2px}
.bar{display:flex;height:24px;border-radius:8px;overflow:hidden;margin:8px 0 6px;border:1px solid var(--line)}
.seg{display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:700;color:#0b0d14;min-width:22px}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--dim)}
.legend .lg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
.legend b{color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:13.2px}
th{position:sticky;top:44px;background:#101320;color:var(--dim);text-align:left;font-size:11px;
 letter-spacing:.06em;text-transform:uppercase;padding:8px 9px;border-bottom:1px solid var(--line);z-index:5}
td{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
tr:hover td{background:rgba(139,124,248,.05)}
td.num{color:var(--dim);font-family:ui-monospace,monospace;font-size:12px}
td.app{min-width:200px} .one{color:var(--dim);font-size:11.8px;margin-top:2px;max-width:300px}
td.api{min-width:110px;font-size:12px} .bw{color:var(--dim)}
td.ev-td{min-width:92px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace} .small{font-size:12px} .dim{color:var(--dim)}
.chip{display:inline-block;border-radius:999px;padding:2.5px 9px;font-size:11px;font-weight:700;margin:1px 2px 1px 0;border:1px solid transparent;white-space:nowrap}
.a-oauth{background:rgba(139,124,248,.16);color:#c4b5fd;border-color:rgba(139,124,248,.35)}
.a-key{background:rgba(56,189,248,.14);color:#7dd3fc;border-color:rgba(56,189,248,.3)}
.a-basic{background:rgba(244,114,182,.14);color:#f9a8d4;border-color:rgba(244,114,182,.3)}
.a-jwt{background:rgba(250,204,21,.13);color:#fde047;border-color:rgba(250,204,21,.28)}
.a-hmac{background:rgba(251,146,60,.14);color:#fdba74;border-color:rgba(251,146,60,.3)}
.a-bot{background:rgba(34,197,94,.13);color:#86efac;border-color:rgba(34,197,94,.3)}
.a-none{background:rgba(148,163,184,.14);color:#cbd5e1;border-color:rgba(148,163,184,.3)}
.acc-free{background:rgba(34,197,94,.15);color:#86efac;border-color:rgba(34,197,94,.35)}
.acc-paid{background:rgba(132,204,22,.15);color:#d9f99d;border-color:rgba(132,204,22,.35)}
.acc-appr{background:rgba(245,158,11,.16);color:#fcd34d;border-color:rgba(245,158,11,.35)}
.acc-ent{background:rgba(239,68,68,.16);color:#fca5a5;border-color:rgba(239,68,68,.4)}
.acc-no{background:rgba(107,114,128,.2);color:#d1d5db;border-color:rgba(107,114,128,.45)}
.v-now{background:rgba(34,197,94,.15);color:#86efac;border-color:rgba(34,197,94,.35)}
.v-friction{background:rgba(245,158,11,.16);color:#fcd34d;border-color:rgba(245,158,11,.35)}
.v-blocked{background:rgba(239,68,68,.16);color:#fca5a5;border-color:rgba(239,68,68,.4)}
.m-off{background:rgba(139,124,248,.18);color:#c4b5fd;border-color:rgba(139,124,248,.4)}
.m-com{background:rgba(56,189,248,.13);color:#7dd3fc;border-color:rgba(56,189,248,.3)}
.m-none{background:rgba(148,163,184,.12);color:#94a3b8;border-color:rgba(148,163,184,.3)}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}
select,input[type=search]{background:var(--card2);color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:8px 11px;font-size:13.5px}
input[type=search]{min-width:210px}
button.tog{background:var(--card2);color:var(--dim);border:1px solid var(--line);border-radius:999px;padding:7px 13px;font-size:12.5px;cursor:pointer}
button.tog.on{background:rgba(139,124,248,.2);color:#c4b5fd;border-color:rgba(139,124,248,.5)}
.minibar{display:flex;height:12px;border-radius:6px;overflow:hidden;background:#222;min-width:130px}
.minibar span{display:block;height:100%}
.brow{display:grid;grid-template-columns:200px 1fr 30px;gap:10px;align-items:center;margin:6px 0;font-size:12.5px}
.blab{color:var(--dim)} .btrack{background:#1b2030;border-radius:6px;height:13px;overflow:hidden}
.bfill{background:linear-gradient(90deg,var(--vio2),var(--vio));height:100%}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:6px 0 2px}
.step{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:13px 14px}
.step .sn{width:28px;height:28px;border-radius:8px;background:rgba(139,124,248,.16);color:#c4b5fd;display:flex;align-items:center;justify-content:center;font-weight:800;margin-bottom:8px}
.step b{font-size:13.5px} .step p{color:var(--dim);font-size:12.6px;margin-top:3px}
.hitl{border:1px solid rgba(56,189,248,.45);background:rgba(56,189,248,.08);border-radius:14px;padding:16px 18px}
.hitl h4{color:#7dd3fc;letter-spacing:.1em;font-size:12.5px}
.hitl ol{margin:10px 0 0 20px} .hitl li{margin:7px 0;font-size:13.8px;color:#dbeafe}
.callout{border:1px solid rgba(245,158,11,.4);background:rgba(245,158,11,.08);border-radius:12px;padding:12px 14px;margin:12px 0 0;font-size:13px;color:#fde68a}
.callout.red{border-color:rgba(239,68,68,.4);background:rgba(239,68,68,.08);color:#fecaca}
.callout.vio{border-color:rgba(139,124,248,.45);background:rgba(139,124,248,.09);color:#ddd6fe}
details{margin-top:6px} summary{cursor:pointer;color:var(--dim);font-size:12px}
details p{font-size:12.3px;color:var(--dim);margin-top:5px}
ul.ev{margin:6px 0 0 18px;font-size:12px}
ul.tight{margin:6px 0 0 18px} ul.tight li{margin:3px 0;font-size:13.2px}
.run code{background:var(--card2);border:1px solid var(--line);border-radius:8px;display:block;padding:11px 14px;margin:8px 0;font-size:12.6px;overflow:auto;color:#c4b5fd;font-family:ui-monospace,monospace}
footer{margin-top:46px;padding:22px 0;border-top:1px solid var(--line);color:var(--dim);font-size:12.5px}
.hl{color:var(--ink);font-weight:700}
table.compact td,table.compact th{padding:6px 8px}
</style>
</head>
<body>
<!-- AGENT-HINTS: Full machine-readable dataset at script#dataset (application/json).
     Sections: #patterns #findings #agent #queues #run. Access enum: {self-serve-free,
     self-serve-paid-or-trial, approval-gated, enterprise-gated, no-public-api}; verdict:
     {build-now, build-with-friction, blocked}; mcp: {official, community, none-found}. -->
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Dataset","name":"Composio 100-app toolkit research",
"description":"Auth, access gating, API surface, MCP presence and buildability verdicts for 100 SaaS apps, produced by an agent pipeline and human-verified.",
"keywords":["Composio","OAuth2","API key","MCP","agent toolkits","SaaS integrations"],
"variableMeasured":["category","auth","access","api_surface","api_breadth","mcp","verdict","blocker","evidence"]}
</script>

<header class="hero"><div class="wrap">
  <div class="kicker">Composio · AI Product Ops Intern · take-home case study</div>
  <h1>100 apps, 100 toolkits? <span class="grad">This research set has a shape — and it's mostly buildable.</span></h1>
  <p class="sub">An agent researched 100 apps for AI-agent toolkits. Human review verified the answers against official docs. Findings first, proof second, receipts always.</p>

  <div class="submit">
    <a class="btn" href="#run">▶ Live case study &amp; deploy</a>
    <a class="btn" href="https://github.com/mukund976/composio-ai-product-intern-assignment" target="_blank" rel="noopener">▶ Source repo</a>
    <span class="dim small">live repo · <span class="mono">verify &rarr; corrections &rarr; build</span> reproduce every number on this page</span>
  </div>

  <div class="tldr">
    <b>TL;DR</b>
    <ul class="tight">
      <li><b>__N__ apps, 10 categories</b> researched and verified: auth · self-serve vs gated · API surface · MCP · buildability · evidence links.</li>
      <li><b>Key pattern:</b> static keys (__STATIC__/100) and OAuth2 (__OAUTH__/100) dominate — __HYBRID__ apps use both. __BUILD_NOW__/100 can be built today; __SS_PCT__% need no sales call.</li>
      <li><b>Main blockers:</b> enterprise/sales gates and approval processes (__BLOCKER_TOP__) — process, not missing technology.</li>
      <li><b>Verified:</b> __S2_PCT__% agreement with official docs on __S2_C__ audited checks (40-app sample — not a claim about every field of all 100). All 188 evidence links are live.</li>
    </ul>
  </div>

  <div class="meta-chips">
    <span>__N__ apps · 10 categories</span>
    <span>__S1_PCT__% → __S2_PCT__% agreement on audited checks</span>
    <span>0 dead evidence links (188 checked)</span>
  </div>
  <div class="covmap">Assignment map → <a href="#findings">category &amp; one-line · auth · self-serve vs gated · API surface · MCP · verdict &amp; blocker · evidence (§2)</a> · <a href="#patterns">patterns (§1)</a> · <a href="#agent">agent + human verification (§3)</a> · <a href="#queues">easy wins vs outreach (§4)</a> · <a href="#run">proof &amp; run (§5)</a></div>
</div></header>

<nav class="sticky"><div class="wrap">
  <a href="#patterns">1 · Patterns</a>
  <a href="#findings">2 · 100-app matrix</a>
  <a href="#agent">3 · Agent + human verification</a>
  <a href="#queues">4 · Easy wins / blockers</a>
  <a href="#run">5 · Proof &amp; run</a>
</div></nav>

<main class="wrap">

<!-- ============ 1 · PATTERNS ============ -->
<section id="patterns">
  <h2><span class="n">01</span>Patterns</h2>
  <p class="lede">The set splits into a large agent-ready majority and a small gated tail — where the blocker is <span class="hl">process (sales, approvals, policy), not technology</span>.</p>

  <div class="grid g2" style="margin-bottom:13px">
    <div class="pattern"><b class="t">1 · Static keys + OAuth2 are the twin standard — usually together.</b>
      <p><b>__STATIC__</b>/100 use a static key and <b>__OAUTH__</b>/100 use OAuth2; <b>__HYBRID__</b> use both. Everything else is niche: Basic, JWT, HMAC signing (__AUTH_HMAC_N__), bot tokens.</p></div>
    <div class="pattern"><b class="t">2 · __SS_PCT__% is self-serveable today.</b>
      <p>__FREE__ apps give free credentials; __PAID__ more are self-serve on a paid plan or trial. Only __APPROVAL__ are approval-gated and __ENTERPRISE__ enterprise-gated.</p></div>
    <div class="pattern"><b class="t">3 · Top blockers are process, not missing APIs.</b>
      <p>__BLOCKER_TOP__ lead the blocker list. Only one app has no API at all (NotebookLM); two are contract-only (PitchBook, Paygent Connect).</p></div>
    <div class="pattern"><b class="t">4 · __MCP_OFF__ apps already ship an official MCP.</b>
      <p>Plus __MCP_COM__ community servers. Connectivity is commoditizing — the toolkit edge is action breadth, auth plumbing and reliability.</p></div>
    <div class="pattern"><b class="t">5 · Self-serve follows category.</b>
      <p>Dev tools &amp; productivity: 20/20 build-now, mostly free. The 6 enterprise gates scatter across CRM (DealCloud), Support (Gladly), Ecommerce (SFCC), Data (Ahrefs) and Finance (Paygent, PitchBook). Ads platforms lead the approval group.</p></div>
    <div class="pattern"><b class="t">6 · Three apps can't be hosted toolkits — that's data, not failure.</b>
      <p>NotebookLM (no public API), Sherlock &amp; Mermaid CLI (local tools → ship as skills), Paygent Connect (no discoverable developer docs).</p></div>
  </div>

  <div class="card">
    <h4>Self-serve vs gated — this 100-app research set</h4>
    __ACCESS_BAR__
  </div>

  <div class="grid g2" style="margin-top:13px">
    <div class="card">
      <h4>Access mix by category (green → red) &amp; build-now rate</h4>
      <table class="compact"><thead><tr><th>Category</th><th>n</th><th>Access</th><th>Build now</th></tr></thead>
      <tbody>__HEAT_ROWS__</tbody></table>
    </div>
    <div class="card">
      <h4>What blocks the __BLOCKED__ non-"build now" apps</h4>
      __BLOCKER_BARS__
    </div>
  </div>
</section>

<!-- ============ 2 · MATRIX ============ -->
<section id="findings">
  <h2><span class="n">02</span>100-app research matrix</h2>
  <p class="lede">Every row: what it does, auth, self-serve vs gated, API surface, MCP, verdict, and evidence links. Expand <b>detail</b> for the full rationale.</p>
  <div class="controls">
    <input type="search" id="q" placeholder="Search app…" aria-label="Search">
    <select id="cat" aria-label="Category"><option value="">All categories</option>__CAT_OPTIONS__</select>
    <button class="tog on" data-f="acc" data-v="self-serve-free">Free</button>
    <button class="tog on" data-f="acc" data-v="self-serve-paid-or-trial">Paid/trial</button>
    <button class="tog on" data-f="acc" data-v="approval-gated">Approval</button>
    <button class="tog on" data-f="acc" data-v="enterprise-gated">Enterprise</button>
    <button class="tog on" data-f="acc" data-v="no-public-api">No API</button>
    <span class="dim small" id="cnt"></span>
  </div>
  <div class="card" style="padding:0;overflow:auto;max-height:72vh">
  <table id="tbl">
    <thead><tr><th>#</th><th>App · what it does</th><th>Category</th><th>Auth</th><th>Self-serve vs gated</th>
    <th>API surface</th><th>MCP</th><th>Verdict</th><th>Evidence</th></tr></thead>
    <tbody>__ROWS__</tbody>
  </table></div>
  <p class="dim small" style="margin-top:8px"><b>Build now</b> = shippable today on public docs + obtainable creds · <b>Build w/ friction</b> = a gate is the main risk · <b>Blocked</b> = not buildable today without partnership.</p>
</section>

<!-- ============ 3 · AGENT + VERIFICATION ============ -->
<section id="agent">
  <h2><span class="n">03</span>Agent + human verification</h2>
  <p class="lede">A four-stage pipeline researched the set. Human review verified it against official docs.</p>

  <div class="steps">
    <div class="step"><div class="sn">1</div><b>Discover</b><p>Find each app's official docs. Check for name collisions (2 traps in this set: Consensus, Pylon).</p></div>
    <div class="step"><div class="sn">2</div><b>Research</b><p>Search + read docs. Record auth, access, API, MCP, verdict — each with a citation.</p></div>
    <div class="step"><div class="sn">3</div><b>Normalize</b><p>Map every finding to one shared schema, validated across all 100 rows.</p></div>
    <div class="step"><div class="sn">4</div><b>Emit</b><p>Write the dataset. The first pass is kept unchanged as the measured baseline.</p></div>
  </div>

  <div class="callout vio" style="margin-top:14px"><b>Tools used.</b> Research ran on an LLM agent with web-search and page-fetch tools (41 searches) plus this repo's pipeline (351 live docs fetches, MCP endpoint probes).
  <b>Composio adapter:</b> <span class="mono">pipeline/composio_runner.py</span> routes research through Composio toolkits when <span class="mono">COMPOSIO_API_KEY</span> is set — implemented and runnable, but not used here (no API key in the sandbox; the assignment required no paid accounts).</div>

  <h3>Human-in-the-loop</h3>
  <div class="hitl">
    <ol>
      <li><b>Checked difficult cases</b> — Human reviewed apps where the agent had low confidence or conflicting evidence.</li>
      <li><b>Verified sources</b> — Human opened the cited official docs and confirmed the agent's claims.</li>
      <li><b>Fixed mistakes</b> — Human corrected wrong auth, access, MCP, or API classifications found during verification.</li>
      <li><b>Final review</b> — Human checked the corrected dataset before publishing the final results.</li>
    </ol>
  </div>

  <div class="grid g3" style="margin-top:13px">
    <div class="card"><h4>Audited agreement vs docs</h4>
      <div class="big vio">__S1_PCT__% → __S2_PCT__%</div>
      <p><b>Agreement with official docs</b> on __S2_C__ audited checks across a 40-app sample — after human fixes. This is a sample result, not a blanket claim about all 100 apps.</p></div>
    <div class="card"><h4>Blind holdout (10 unseen apps)</h4>
      <div class="big grn">50 / 50</div>
      <p>Unseen apps agreed in both passes — the review rules didn't overfit the sample.</p></div>
    <div class="card"><h4>Evidence links</h4>
      <div class="big blu">0 dead</div>
      <p>All 188 cited links live-checked. 29 dead links were found and replaced during verification.</p></div>
  </div>

  <h3>What we got wrong — kept on purpose</h3>
  <div class="card" style="padding:0;overflow:auto"><table class="compact">
    <thead><tr><th>#</th><th>App</th><th>Field</th><th>Agent said</th><th>Docs said</th></tr></thead>
    <tbody>__MISS_ROWS__</tbody></table></div>
  <p class="small dim" style="margin-top:8px">6 of the 195 audited checks were wrong at first: a phantom OAuth (Pylon), three over-listed auth methods, one wrong auth family (Neo4j), one wrong MCP label (Pumble). A later full sweep of all 100 rows found 5 more classification errors outside the sample (e.g. Discord's MCP label) — all fixed before publish.</p>

  <div class="callout red"><b>Apps that defeated the agent:</b> Paygent Connect — an NMI white-label reseller with no public developer docs (recorded as blocked, not guessed). NotebookLM has no API at all.</div>
</section>

<!-- ============ 4 · QUEUES ============ -->
<section id="queues">
  <h2><span class="n">04</span>Easy wins / blockers</h2>
  <div class="grid g3">
    <div class="card"><h4>Ship queue · __EASY_N__ easy wins</h4>
      <p class="small dim">Build-now + self-serveable + broad API. First sprint:</p>
      <ul class="tight">__EASY_LIST__</ul></div>
    <div class="card"><h4>Outreach queue · __OUTREACH_N__ apps</h4>
      <p class="small dim">Approval or enterprise gates. Start conversations early:</p>
      <ul class="tight">__OUTREACH_LIST__</ul></div>
    <div class="card"><h4>Shelf · blocked / reclassify</h4>
      <p class="small dim">Not hosted-toolkit material today:</p>
      <ul class="tight">__BLOCKED_LIST__</ul></div>
  </div>
</section>

<!-- ============ 5 · PROOF & RUN ============ -->
<section id="run">
  <h2><span class="n">05</span>Proof, GitHub &amp; run instructions</h2>
  <div class="submit" style="margin-top:4px">
    <a class="btn" href="https://github.com/mukund976/composio-ai-product-intern-assignment" target="_blank" rel="noopener">▶ github.com/mukund976/composio-ai-product-intern-assignment</a>
    <span class="dim small">this page = <span class="mono">site/index.html</span> · serve: <span class="mono">python3 -m http.server 8000 -d site</span> · deploy: <span class="mono">npx netlify-cli deploy --prod --dir site</span></span>
  </div>
  <div class="card run">
    <code># clone + install
git clone https://github.com/mukund976/composio-ai-product-intern-assignment.git &amp;&amp; cd composio-ai-product-intern-assignment
pip install -r pipeline/requirements.txt

# research (validate all 100 rows; re-run any app live)
python3 pipeline/agent.py validate
python3 pipeline/agent.py research --id 59

# verify against live docs (reproduces the numbers below)
python3 pipeline/verify.py check --pass data/final_research.json
python3 pipeline/verify.py score --pass data/pass1_research.json   # 189/195 = 96.9% agreement
python3 pipeline/verify.py score --pass data/final_research.json   # 195/195 = 100% agreement (audited checks)

# human corrections -> final dataset -> this page
python3 pipeline/apply_corrections.py
python3 pipeline/analyze.py &amp;&amp; python3 pipeline/build_site.py</code>
    <p class="small dim">The same commands live in the repo README. Deep verification detail (correction ledger, probe logs, ground truth) is in <span class="mono">data/</span> and <span class="mono">reports/</span>.</p>
  </div>
  <div class="controls">
    <button class="tog" id="dl">Download dataset (final_research.json)</button>
    <button class="tog" id="tg">Show/hide machine-readable data</button>
  </div>
  <pre id="raw" class="card mono small" style="display:none;max-height:360px;overflow:auto"></pre>
</section>

<footer><div class="wrap">
  Composio AI Product Ops Intern take-home · 100 apps / 10 categories ·
  verified against official docs on a 40-app audit sample (195 checks) with a full 100-row link sweep ·
  errors and defeated apps are part of the story, not footnotes.
</div></footer>
</main>

<script type="application/json" id="dataset">__DATASET_JSON__</script>
<script>
(function(){
  const rows=[...document.querySelectorAll('#tbl tbody tr')];
  const q=document.getElementById('q'), cat=document.getElementById('cat'), cnt=document.getElementById('cnt');
  const togs=[...document.querySelectorAll('button.tog[data-f]')];
  function apply(){
    const term=q.value.trim().toLowerCase(), c=cat.value;
    const accOn=togs.filter(t=>t.dataset.f==='acc'&&t.classList.contains('on')).map(t=>t.dataset.v);
    let n=0;
    rows.forEach(r=>{
      const ok=(!term||r.dataset.name.includes(term)||r.textContent.toLowerCase().includes(term))
        &&(!c||r.dataset.cat===c)&&accOn.includes(r.dataset.acc);
      r.style.display=ok?'':'none'; if(ok)n++;
    });
    cnt.textContent=n+' / '+rows.length+' apps';
  }
  q.addEventListener('input',apply); cat.addEventListener('change',apply);
  togs.forEach(t=>t.addEventListener('click',()=>{t.classList.toggle('on');apply();}));
  apply();
  const raw=document.getElementById('raw'), ds=document.getElementById('dataset');
  raw.textContent=JSON.stringify(JSON.parse(ds.textContent),null,2);
  document.getElementById('tg').onclick=()=>{raw.style.display=raw.style.display==='none'?'block':'none';};
  document.getElementById('dl').onclick=()=>{
    const blob=new Blob([ds.textContent],{type:'application/json'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download='final_research.json';a.click();};
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
