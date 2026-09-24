#!/usr/bin/env python3
"""
pipeline/analyze.py — pattern mining over the final 100-app dataset.

Emits reports/analysis.json (machine-readable, used by build_site.py and
citable in the case study). Prints a human summary.

  python3 pipeline/analyze.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def auth_families(rec) -> set:
    SYNONYM = {"API key": "static-key", "Token": "static-key", "JWT": "jwt", "JWT key-pair": "jwt"}
    return {SYNONYM.get(a, a.lower()) for a in rec.get("auth", [])}


def main() -> None:
    data = json.loads((ROOT / "data" / "final_research.json").read_text())
    recs = data["records"]
    cats = sorted({r["category"] for r in recs})

    auth_counter = Counter()
    hybrid = 0
    for r in recs:
        fams = auth_families(r)
        for f in fams:
            auth_counter[f] += 1
        if "oauth2" in fams and "static-key" in fams:
            hybrid += 1

    access_counter = Counter(r["access"] for r in recs)
    verdict_counter = Counter(r["verdict"] for r in recs)
    mcp_counter = Counter(r["mcp"] for r in recs)
    breadth_counter = Counter(r["api_breadth"] for r in recs)
    surface_counter = Counter()
    for r in recs:
        for s in r.get("api_surface", []):
            surface_counter[s] += 1

    access_by_cat = defaultdict(Counter)
    verdict_by_cat = defaultdict(Counter)
    for r in recs:
        access_by_cat[r["category"]][r["access"]] += 1
        verdict_by_cat[r["category"]][r["verdict"]] += 1

    # blocker taxonomy (from blocker strings on non-build-now rows)
    def blocker_class(r) -> str:
        b = (r.get("blocker") or "").lower()
        if r["access"] == "no-public-api":
            return "no public API"
        if r["verdict"] == "blocked":
            return "contract-only / invisible API"
        if "outreach" in b or "enterprise" in b or "contract" in b:
            return "enterprise / sales gate"
        if "approval" in b or "partner" in b or "review" in b or "verification" in b or "policy" in b:
            return "approval / policy friction"
        if "plan" in b or "paid" in b or "paywall" in b or "qbo" in b:
            return "paid-plan gate"
        if "local" in b or "cli" in b or "not a saas" in b or "not an api" in b or "no hosted api" in b:
            return "local-only (CLI/OSS)"
        if "fragment" in b or "split" in b:
            return "fragmented surface"
        return "other"

    blockers = Counter(blocker_class(r) for r in recs if r["verdict"] != "build-now")

    easy_wins = [r for r in recs if r["verdict"] == "build-now"
                 and r["access"] in ("self-serve-free", "self-serve-paid-or-trial")
                 and r["api_breadth"] in ("very-broad", "broad")]
    outreach = [r for r in recs if r["access"] in ("approval-gated", "enterprise-gated")]
    blocked = [r for r in recs if r["verdict"] == "blocked"]
    mcp_official = [r for r in recs if r["mcp"] == "official"]
    free_now = [r for r in recs if r["access"] == "self-serve-free"]

    analysis = {
        "n": len(recs),
        "auth_family_counts": dict(auth_counter.most_common()),
        "hybrid_oauth_plus_static": hybrid,
        "access_counts": dict(access_counter),
        "access_pct_selfserveable": round(100 * (access_counter["self-serve-free"] + access_counter["self-serve-paid-or-trial"]) / len(recs), 1),
        "verdict_counts": dict(verdict_counter),
        "mcp_counts": dict(mcp_counter),
        "breadth_counts": dict(breadth_counter),
        "surface_counts": dict(surface_counter),
        "access_by_category": {c: dict(access_by_cat[c]) for c in cats},
        "verdict_by_category": {c: dict(verdict_by_cat[c]) for c in cats},
        "blocker_classes": dict(blockers.most_common()),
        "easy_wins": [{"id": r["id"], "name": r["name"], "category": r["category"], "breadth": r["api_breadth"]} for r in easy_wins],
        "needs_outreach": [{"id": r["id"], "name": r["name"], "category": r["category"], "access": r["access"], "blocker": r.get("blocker", "")} for r in outreach],
        "blocked": [{"id": r["id"], "name": r["name"], "category": r["category"], "blocker": r.get("blocker", "")} for r in blocked],
        "mcp_official": [{"id": r["id"], "name": r["name"], "category": r["category"]} for r in mcp_official],
        "free_creds_today": [{"id": r["id"], "name": r["name"]} for r in free_now],
        "category_order": cats,
    }
    out = ROOT / "reports" / "analysis.json"
    out.write_text(json.dumps(analysis, indent=2))

    print(f"n={analysis['n']}")
    print("auth families:", analysis["auth_family_counts"], f"| hybrid oauth2+static: {hybrid}")
    print("access:", analysis["access_counts"], f"| self-serveable {analysis['access_pct_selfserveable']}%")
    print("verdicts:", analysis["verdict_counts"])
    print("mcp:", analysis["mcp_counts"])
    print("blockers:", analysis["blocker_classes"])
    print(f"easy wins: {len(easy_wins)} | outreach: {len(outreach)} | blocked: {len(blocked)} | official MCP: {len(mcp_official)}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
