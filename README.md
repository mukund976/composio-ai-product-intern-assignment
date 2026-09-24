# Composio AI Product Ops Intern — 100-App Toolkit Research

## What I built

I built an agent-assisted research pipeline that studied **100 apps across 10 categories** to see how ready each one is for AI-agent toolkits. For every app it recorded the authentication method, whether access is self-serve or gated, the API surface, MCP support, a buildability verdict, and the evidence behind every claim. The agent produced the raw findings; human review then verified them against official documentation. The result is a single, self-contained HTML case study backed by this runnable repository.

## Key Results

Verified results on audited checks — not an overall accuracy claim.

- **100 apps** across **10 categories**
- **195 audited checks** against official documentation
- **96.9% → 100% agreement with docs on audited checks** (first pass → after human review)
- **5 additional row errors** found and fixed during the full-set sweep
- **20 dead evidence links** found and fixed during the full-set sweep
- **0 dead evidence links remaining** — all 188 evidence links live-checked

## View the Case Study

- **Live case study:** https://mukund976.github.io/composio-ai-product-intern-assignment/
- **GitHub repository:** https://github.com/mukund976/composio-ai-product-intern-assignment

## How It Worked

**Research → Structure → Verify → Human Review → Final Dataset**

- **Research** — The agent searched and read each app's official documentation.
- **Structure** — Findings were mapped to one shared schema: auth, access, API, MCP, verdict, evidence.
- **Verify** — Every cited link and claim was checked against live documentation.
- **Human Review** — A person reviewed the difficult cases and corrected mistakes.
- **Final Dataset** — Corrections were applied and the final dataset was published.

## Human Verification

1. Checked difficult cases where evidence was unclear or conflicting.
2. Opened cited documentation and verified the claims.
3. Corrected mistakes in authentication, API, access, or MCP classifications.
4. Reviewed the final corrected dataset before publishing.

## How to Run

```bash
git clone https://github.com/mukund976/composio-ai-product-intern-assignment.git
cd composio-ai-product-intern-assignment
pip install -r pipeline/requirements.txt

# check that the 100-app research set is complete and well-formed
python3 pipeline/agent.py validate

# live-check every cited evidence link and re-run the claim checks (needs internet)
python3 pipeline/verify.py check --pass data/final_research.json --out reports/final_verification.json
```

- **`agent.py validate`** — confirms all 100 records are complete and consistent (you can also re-run research for any single app).
- **`verify.py check`** — fetches every evidence URL and re-checks the claims, writing a verification report.

## Important Files

- `site/index.html` — the case study
- `apps.json` — the 100-app research set
- `pipeline/agent.py` — the research agent
- `pipeline/verify.py` — the verification
- `data/final_research.json` — the final dataset
- `data/corrections.json` — human corrections

## Honest Notes

- Some apps have gated or unavailable APIs.
- Some documentation is difficult for automated tools to access.
- The Composio adapter was implemented but was not used to produce the final submission.
- Human verification was therefore an important part of the process.
