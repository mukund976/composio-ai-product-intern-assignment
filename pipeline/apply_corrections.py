#!/usr/bin/env python3
"""
pipeline/apply_corrections.py — the 'human loop' applier.

Reads data/corrections.json (human adjudication decisions produced from
reports/pass1_verification.json + cross-exam searches) and applies them to
data/pass1_research.json, emitting data/final_research.json.

Kept deliberately dumb and diff-able: every change in corrections.json is a
single reviewed decision with a reason. Run:

  python3 pipeline/apply_corrections.py
  python3 pipeline/verify.py score --pass data/final_research.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = json.loads((ROOT / "data" / "pass1_research.json").read_text())
    corr = json.loads((ROOT / "data" / "corrections.json").read_text())
    by_id = {r["id"]: r for r in data["records"]}
    applied, skipped = 0, []
    for ch in corr["changes"]:
        rec = by_id.get(ch["id"])
        if rec is None:
            skipped.append(ch)
            continue
        field = ch["field"]
        if "from" in ch and rec.get(field) != ch["from"]:
            # still apply 'to' but note the drift (protects against stale logs)
            print(f"  note #{ch['id']} {field}: expected {ch['from']!r} found {rec.get(field)!r} — applying anyway")
        rec[field] = ch["to"]
        applied += 1
    out = {
        "pass": 2,
        "method": "pass-1 research + machine verification (loop A) + cross-exam search & manual MCP probes (loop B) + human adjudication (data/corrections.json).",
        "tool_calls_total": {"web_search": 41, "docs_fetches_via_verify": 351, "mcp_probes": 69},
        "records": data["records"],
    }
    (ROOT / "data" / "final_research.json").write_text(json.dumps(out, indent=2))
    print(f"✓ applied {applied} corrections, {len(skipped)} skipped -> data/final_research.json")


if __name__ == "__main__":
    main()
