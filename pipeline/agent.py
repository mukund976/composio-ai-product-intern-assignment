#!/usr/bin/env python3
"""
Composio-100 research agent — pipeline/agent.py

Stage model (see README):
  1. DISCOVER   — resolve each app to authoritative docs roots
  2. RESEARCH   — gather auth / access / API-surface / MCP evidence per app
  3. NORMALIZE  — map findings onto the shared enum schema (apps.json meta)
  4. EMIT       — write data/passN_research.json

How this ran for the submission (honest notes):
  * The RESEARCH stage was executed by an LLM research agent with web-search and
    page-fetch tools (21 targeted searches; 100 apps digested). Tool outputs are
    summarized in the `evidence` + `source` fields of each record.
  * This script is the runnable orchestrator around that stage: it loads the app
    registry, validates/normalizes records against the schema, and can re-run
    research for individual apps via pluggable tools (Composio toolkit runner in
    composio_runner.py, or a naive docs-fetch fallback here).
  * Human touchpoints are listed in data/verification_log.json (adjudications).

Usage:
  python3 pipeline/agent.py validate            # schema-validate pass1 data
  python3 pipeline/agent.py research --id 59    # live re-research of one app
  python3 pipeline/agent.py research --all --limit 5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS_FILE = ROOT / "apps.json"
PASS1 = ROOT / "data" / "pass1_research.json"

AUTH_ENUM = {"OAuth2", "OAuth1", "API key", "Basic", "Token", "JWT", "Bot token", "HMAC",
             "JWT key-pair", "Digest", "None"}
ACCESS_ENUM = {"self-serve-free", "self-serve-paid-or-trial", "approval-gated",
               "enterprise-gated", "no-public-api"}
VERDICT_ENUM = {"build-now", "build-with-friction", "blocked"}
MCP_ENUM = {"official", "community", "none-found"}
SURFACE_ENUM = {"REST", "GraphQL", "SOAP", "Bulk", "Metadata", "CLI", "None"}
BREADTH_ENUM = {"very-broad", "broad", "moderate", "narrow"}


def load_registry():
    return json.loads(APPS_FILE.read_text())


def load_pass1():
    return json.loads(PASS1.read_text())


def validate() -> int:
    """Schema + completeness validation for the research dataset."""
    reg = load_registry()["apps"]
    data = load_pass1()["records"]
    errors = []
    ids = {a["id"] for a in reg}
    rec_ids = {r["id"] for r in data}
    if ids != rec_ids:
        errors.append(f"id mismatch: registry-only={sorted(ids - rec_ids)} rec-only={sorted(rec_ids - ids)}")
    for r in data:
        where = f"#{r['id']} {r['name']}"
        for a in r.get("auth", []):
            if a not in AUTH_ENUM:
                errors.append(f"{where}: auth '{a}' not in enum")
        if r.get("access") not in ACCESS_ENUM:
            errors.append(f"{where}: access '{r.get('access')}' not in enum")
        if r.get("verdict") not in VERDICT_ENUM:
            errors.append(f"{where}: verdict '{r.get('verdict')}' not in enum")
        if r.get("mcp") not in MCP_ENUM:
            errors.append(f"{where}: mcp '{r.get('mcp')}' not in enum")
        if r.get("api_breadth") not in BREADTH_ENUM:
            errors.append(f"{where}: api_breadth '{r.get('api_breadth')}' not in enum")
        if not r.get("evidence"):
            errors.append(f"{where}: missing evidence URL(s)")
        if not r.get("one_liner"):
            errors.append(f"{where}: missing one_liner")
        if r.get("verdict") != "build-now" and not r.get("blocker"):
            errors.append(f"{where}: non-build-now verdict needs a blocker")
    if errors:
        print(f"✗ {len(errors)} validation error(s):")
        for e in errors:
            print("  -", e)
        return 1
    print(f"✓ {len(data)} records valid against schema ({len(reg)} apps in registry)")
    return 0


# ---------------------------------------------------------------- research ---
def fetch_docs_text(url: str, max_chars: int = 20000) -> str:
    """Naive page-fetch tool adapter (fallback when no search tool is wired)."""
    import requests
    from bs4 import BeautifulSoup
    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "composio-research-agent/1.0 (take-home assignment)"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = re.sub(r"\n{3,}", "\n\n", soup.get_text(" ", strip=True))
        return text[:max_chars]
    except Exception as exc:  # noqa: BLE001
        return f"[fetch failed: {exc}]"


def research_app(app: dict, use_composio: bool = False) -> dict:
    """RESEARCH stage for one app. Pluggable tools:
    1) Composio runner (composio_runner.py) when use_composio and key present
    2) local docs fetch + heuristic extraction (this file, offline-friendly)
    """
    if use_composio:
        try:
            from composio_runner import research_via_composio
            return research_via_composio(app)
        except Exception as exc:  # noqa: BLE001
            print(f"  composio runner unavailable ({exc}); falling back", file=sys.stderr)
    hint_url = app.get("website", "")
    if hint_url and not hint_url.startswith("http"):
        hint_url = "https://" + hint_url
    text = fetch_docs_text(hint_url) if hint_url else ""
    hits = {
        "oauth": bool(re.search(r"oauth\s*2|oauth2|authorization code|pkce", text, re.I)),
        "api_key": bool(re.search(r"api[ -]?key|x-api-key|secret key|access token", text, re.I)),
        "basic": bool(re.search(r"basic auth|http basic", text, re.I)),
        "graphql": bool(re.search(r"graphql", text, re.I)),
        "rest": bool(re.search(r"\brest\b|openapi|swagger", text, re.I)),
        "mcp": bool(re.search(r"model context protocol|\bmcp\b", text, re.I)),
        "trial_free": bool(re.search(r"free (tier|plan|trial)|get started", text, re.I)),
        "sales": bool(re.search(r"contact (sales|us)|request a demo|talk to sales", text, re.I)),
    }
    return {"id": app["id"], "name": app["name"], "fetched": hint_url,
            "heuristic_hits": hits, "text_chars": len(text)}


def main():
    ap = argparse.ArgumentParser(description="Composio-100 research agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    rp = sub.add_parser("research")
    rp.add_argument("--id", type=int)
    rp.add_argument("--all", action="store_true")
    rp.add_argument("--limit", type=int, default=10)
    rp.add_argument("--composio", action="store_true",
                    help="route research through Composio toolkits (needs COMPOSIO_API_KEY)")
    args = ap.parse_args()

    if args.cmd == "validate":
        sys.exit(validate())

    if args.cmd == "research":
        reg = load_registry()["apps"]
        targets = [a for a in reg if args.id in (None, a["id"])][: None if args.id else args.limit]
        if args.id:
            targets = [a for a in reg if a["id"] == args.id]
        out = [research_app(a, use_composio=args.composio) for a in targets]
        out_path = ROOT / "data" / "agent_research_run.json"
        out_path.write_text(json.dumps(out, indent=2))
        print(f"✓ wrote {out_path} ({len(out)} apps)")


if __name__ == "__main__":
    main()
