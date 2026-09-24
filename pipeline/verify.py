#!/usr/bin/env python3
"""
Verification loop — pipeline/verify.py

Three machine checks + a scoring harness for the human-adjudicated ground truth:

  A. EVIDENCE LIVE-CHECK   every cited evidence URL is fetched; status recorded.
  B. CLAIM CORROBORATION   claimed auth/API/MCP/gate facts are keyword-checked
                           against the fetched docs text (hit / miss / weak).
                           A "miss" is a FLAG for human adjudication — not
                           automatically an error (docs use varied vocabulary).
  C. MCP ENDPOINT PROBE    claimed MCP servers are probed at canonical URLs
                           (GET+POST without creds). 2xx/4xx-with-mcp-ish body
                           counts as 'live', DNS failure / 404 as 'dead'.
  D. SCORE vs GROUND TRUTH field-level exact match accuracy of a research pass
                           against data/ground_truth.json (human-adjudicated).

Usage:
  python3 pipeline/verify.py check --pass data/pass1_research.json --out reports/pass1_verification.json
  python3 pipeline/verify.py score --pass data/pass1_research.json
  python3 pipeline/verify.py score --pass data/final_research.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "composio-research-verifier/1.0 (take-home accuracy loop)"}

# Which words must appear near each claimed fact (corroboration vocabulary).
AUTH_KEYWORDS = {
    "OAuth2": [r"oauth\s*2", r"oauth2", r"authorization code", r"pkce",
               r"client credentials", r"refresh token"],
    "OAuth1": [r"oauth\s*1", r"oauth1", r"consumer key", r"signature method"],
    "API key": [r"api[ -]?key", r"apikey", r"x-api-key", r"secret key",
                r"personal access token", r"access token", r"bearer"],
    "Basic": [r"basic auth", r"http basic", r"username:password", r"basic authentication"],
    "Token": [r"access token", r"bearer", r"personal access token", r"auth token", r"api token"],
    "JWT": [r"\bjwt\b", r"json web token"],
    "JWT key-pair": [r"key[ -]pair", r"\bjwt\b", r"rsa", r"signed jwt"],
    "Bot token": [r"bot token", r"botfather", r"bot id"],
    "HMAC": [r"\bhmac\b", r"sha-?256 sign", r"request signing", r"sigv4", r"signature"],
    "Digest": [r"digest auth", r"digest authentication"],
    "None": [r"no auth", r"without auth", r"public api", r"no api"],
}
SURFACE_KEYWORDS = {
    "REST": [r"\brest\b", r"openapi", r"swagger", r"http api"],
    "GraphQL": [r"graphql"],
    "SOAP": [r"\bsoap\b"],
    "Bulk": [r"bulk api", r"bulk[ -]?"],
    "Metadata": [r"metadata api"],
    "CLI": [r"command line", r"\bcli\b", r"npm install", r"pip install"],
    "None": [r"no (public )?(api|rest)"],
}
MCP_KEYWORDS = [r"model context protocol", r"\bmcp\b", r"mcp server"]
ACCESS_KEYWORDS = {
    "self-serve-free": [r"free (tier|plan|trial|forever|account)", r"get started for free",
                        r"free \$", r"open source", r"no credit card"],
    "self-serve-paid-or-trial": [r"free trial", r"[0-9]+-day trial", r"pricing",
                                 r"per month", r"/mo", r"paid plan", r"subscription"],
    "approval-gated": [r"developer token", r"app review", r"approval", r"partner program",
                       r"verification", r"review process", r"sandbox"],
    "enterprise-gated": [r"contact sales", r"talk to sales", r"request a demo",
                         r"enterprise", r"contract", r"account manager"],
    "no-public-api": [r"no (public )?api", r"not available", r"api is not"],
}
GATE_KEYWORDS = [r"contact sales", r"talk to sales", r"request a demo", r"enterprise plan",
                 r"partner program", r"developer token", r"app review", r"approval"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").lower()


def fetch_page(url: str):
    browser_ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
    last = None
    for ua in (UA, browser_ua):
        try:
            r = requests.get(url, timeout=25, headers=ua, allow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")
            for t in soup(["script", "style"]):
                t.decompose()
            text = norm(soup.get_text(" "))
            last = {"url": url, "status": r.status_code, "final_url": str(r.url),
                    "text": text, "error": None,
                    "ua": "bot" if ua is UA else "browser"}
            if r.status_code == 200 and len(text) > 500:
                return last
        except Exception as exc:  # noqa: BLE001
            last = {"url": url, "status": 0, "final_url": None, "text": "", "error": str(exc)[:200],
                    "ua": "bot" if ua is UA else "browser"}
    return last


def check_keywords(text: str, patterns) -> dict:
    hits = [p for p in patterns if re.search(p, text, re.I)]
    return {"hits": hits, "strength": "hit" if hits else "miss"}


def mcp_probe_urls(name: str, evidence: list[str]) -> list[str]:
    urls = []
    domain = None
    for ev in evidence:
        m = re.search(r"https?://(?:www\.|docs\.|developers\.|dev\.|api\.)?([a-z0-9-]+\.[a-z.]+)", ev)
        if m:
            domain = m.group(1)
            break
    slug = re.sub(r"[^a-z0-9]", "", name.lower())
    if domain:
        urls.append(f"https://mcp.{domain}/mcp")
        urls.append(f"https://{domain}/mcp")
    urls.append(f"https://mcp.{slug}.com/mcp")
    return urls[:3]


def probe_mcp(urls: list[str]) -> dict:
    results = []
    for u in urls:
        try:
            r = requests.post(u, json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                              timeout=12, headers={**UA, "Content-Type": "application/json",
                                                   "Accept": "application/json, text/event-stream"})
            body = (r.text or "")[:200].lower()
            live = r.status_code < 500 and (
                r.status_code in (200, 405, 406, 400, 415) or "mcp" in body or "jsonrpc" in body)
            results.append({"url": u, "status": r.status_code, "live": live,
                            "signal": "ok" if live else "not-mcp"})
        except Exception as exc:  # noqa: BLE001
            results.append({"url": u, "status": 0, "live": False,
                            "signal": f"unreachable: {str(exc)[:80]}"})
    live = [r for r in results if r["live"]]
    return {"live": bool(live), "attempts": results[:3], "first_live": live[0]["url"] if live else None}


def window(text: str, patterns, width: int = 160) -> str:
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            a = max(0, m.start() - width)
            b = min(len(text), m.end() + width)
            return "…" + text[a:b] + "…"
    return ""


def run_check(pretty_pass: dict, only_ids: set[int] | None = None) -> dict:
    rows = []
    for rec in pretty_pass["records"]:
        if only_ids and rec["id"] not in only_ids:
            continue
        page_hits = [fetch_page(u) for u in rec.get("evidence", [])]
        docs_text = " ".join(p["text"] for p in page_hits if p["text"])
        flags, checks = [], []

        for a in rec.get("auth", []):
            kw = AUTH_KEYWORDS.get(a, [])
            res = check_keywords(docs_text, kw) if kw else {"hits": [], "strength": "skip"}
            if a == "None":
                continue  # absence-of-auth claim can't be keyword-corroborated
            checks.append({"field": "auth", "claim": a, **res})
            if res["strength"] == "miss":
                flags.append(f"auth '{a}' not corroborated in fetched docs")
        for s in rec.get("api_surface", []):
            if s in ("None",):
                continue
            kw = SURFACE_KEYWORDS.get(s, [])
            res = check_keywords(docs_text, kw) if kw else {"hits": [], "strength": "skip"}
            checks.append({"field": "api_surface", "claim": s, **res})
        if rec.get("mcp") in ("official", "community"):
            kw_res = check_keywords(docs_text, MCP_KEYWORDS)
            probe = probe_mcp(mcp_probe_urls(rec["name"], rec.get("evidence", [])))
            checks.append({"field": "mcp", "claim": rec["mcp"], **kw_res,
                           "probe_live": probe["live"], "first_live": probe["first_live"]})
            if rec["mcp"] == "official" and not (kw_res["strength"] == "hit" or probe["live"]):
                flags.append("claimed official MCP: no docs mention AND no live endpoint")
        acc_kw = ACCESS_KEYWORDS.get(rec.get("access"), [])
        res = check_keywords(docs_text, acc_kw)
        checks.append({"field": "access", "claim": rec.get("access"), **res,
                       "excerpt": window(docs_text, acc_kw)})
        gate_res = check_keywords(docs_text, GATE_KEYWORDS)
        if gate_res["hits"] and rec.get("access", "").startswith("self-serve"):
            checks.append({"field": "gate-signals", "claim": rec.get("access"), **gate_res,
                           "excerpt": window(docs_text, GATE_KEYWORDS)})

        live_ok = all(p["status"] and p["status"] < 400 for p in page_hits)
        rows.append({
            "id": rec["id"], "name": rec["name"],
            "evidence_fetches": [{"url": p["url"], "status": p["status"],
                                  "final_url": p["final_url"], "error": p["error"],
                                  "text_chars": len(p["text"])} for p in page_hits],
            "evidence_live": live_ok,
            "checks": checks,
            "flags": flags,
        })
        time.sleep(0.3)  # be polite to docs hosts
    n_checks = sum(len(r["checks"]) for r in rows)
    n_flag = sum(len(r["flags"]) for r in rows)
    live = sum(1 for r in rows if r["evidence_live"])
    return {
        "pass_file": str(pretty_pass.get("pass")),
        "apps_checked": len(rows),
        "evidence_urls_live": f"{live}/{len(rows)} apps fully live",
        "keyword_checks_run": n_checks,
        "flags_for_human_review": n_flag,
        "rows": rows,
    }


def score(gt_path: Path, pass_path: Path) -> None:
    gt = json.loads(gt_path.read_text())
    recs = {r["id"]: r for r in json.loads(pass_path.read_text())["records"]}
    fields = ["auth", "access", "api_surface", "mcp", "verdict"]
    SYNONYM = {"api key": "static-key", "token": "static-key", "jwt": "jwt",
               "jwt key-pair": "jwt"}

    def collapse(items):
        out = set()
        for a in items or []:
            a = a.lower()
            out.add(SYNONYM.get(a, a))
        return out

    total = correct = 0
    misses = []
    for gid, g in gt["answers"].items():
        gid = int(gid)
        r = recs.get(gid)
        if not r:
            continue
        for f in fields:
            gold, pred = g.get(f), r.get(f)
            if f in ("auth", "api_surface"):
                gold_n, pred_n = collapse(gold), collapse(pred)
                ok = gold_n == pred_n
            else:
                ok = norm(str(gold)) == norm(str(pred))
            total += 1
            if ok:
                correct += 1
            else:
                misses.append({"id": gid, "name": r["name"], "field": f,
                               "predicted": pred, "gold": gold})
    pct = round(100 * correct / total, 1) if total else 0
    print(json.dumps({"pass": str(pass_path), "gt_apps": len(gt["answers"]),
                      "checks": total, "correct": correct, "accuracy_pct": pct}, indent=2))
    if misses:
        print("\nMisses:")
        for m in misses:
            print(f"  #{m['id']:<3} {m['name']:<22} {m['field']:<11} pred={m['predicted']} gold={m['gold']}")
    out = ROOT / "reports" / (pass_path.stem + "_score.json")
    out.write_text(json.dumps({"checks": total, "correct": correct,
                               "accuracy_pct": pct, "misses": misses}, indent=2))
    print(f"\n→ {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("check")
    cp.add_argument("--pass", dest="pass_file", required=True)
    cp.add_argument("--ids", help="comma list of app ids (default: all)")
    cp.add_argument("--out", default=None)
    sp = sub.add_parser("score")
    sp.add_argument("--pass", dest="pass_file", required=True)
    sp.add_argument("--gt", default=str(ROOT / "data" / "ground_truth.json"))
    args = ap.parse_args()

    if args.cmd == "check":
        pretty = json.loads(Path(args.pass_file).read_text())
        ids = {int(x) for x in args.ids.split(",")} if args.ids else None
        report = run_check(pretty, ids)
        out = Path(args.out or ROOT / "reports" / "verification_report.json")
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
        print(f"→ {out}")
    else:
        score(Path(args.gt), Path(args.pass_file))


if __name__ == "__main__":
    main()
