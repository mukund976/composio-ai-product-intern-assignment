# composio-ai-product-intern-assignment — 100-app toolkit research, built as an agent pipeline

**Take-home deliverable for Composio's AI Product Ops Intern role.** One agent pipeline researched 100 apps
(auth · self-serve vs gated · API surface · MCP · buildability · evidence), then machine + human verification
loops stress-tested every answer. Result: **96.9% → 100% agreement with docs on 195 audited checks**, a full-set
sweep of all 100 rows that found + fixed 5 further row errors and 20 dead links, and **0 dead evidence links**.

---

## Links (start here)

| | |
|---|---|
| **Live case study (HTML)** | **https://mukund976.github.io/composio-ai-product-intern-assignment/** (GitHub Pages) · source: `site/index.html`, self-contained · local: `python3 -m http.server 8000 -d site` |
| **Source repo** | this repo (`composio-ai-product-intern-assignment/`) → publish with `git remote add origin https://github.com/mukund976/composio-ai-product-intern-assignment && git push -u origin main` |

---

## Run the chain — exact sequence (Python 3.10+, network required for steps 2–3)

```bash
# 0 · GET THE CODE
git clone https://github.com/mukund976/composio-ai-product-intern-assignment.git
cd composio-ai-product-intern-assignment

# 1 · INSTALL
pip install -r pipeline/requirements.txt            # requests + beautifulsoup4

# 2 · RESEARCH  (the dataset is included; these re-run/extend the research stage)
python3 pipeline/agent.py validate                   # schema-gate all 100 rows (instant)
python3 pipeline/agent.py research --id 59           # live re-research of one app (docs fetch + heuristics)
python3 pipeline/agent.py research --all --limit 5   # batch mode; add --composio to route via Composio toolkits
#   (pass-1 output for all 100 is preserved at data/pass1_research.json — the measured baseline)

# 3 · VERIFY  (the live audit trigger — fetches every cited URL, probes MCP endpoints)
python3 pipeline/verify.py check --pass data/pass1_research.json --out reports/pass1_verification.json
python3 pipeline/verify.py check --pass data/final_research.json --out reports/final_verification.json
python3 pipeline/verify.py score --pass data/pass1_research.json  # 189/195 = 96.9% agreement
python3 pipeline/verify.py score --pass data/final_research.json  # 195/195 = 100% agreement on audited checks

# 4 · CORRECTIONS  (apply the human adjudication ledger -> final dataset)
python3 pipeline/apply_corrections.py                # data/corrections.json -> data/final_research.json

# 5 · GENERATE HTML
python3 pipeline/analyze.py                          # pattern mining -> reports/analysis.json
python3 pipeline/build_site.py                       # -> site/index.html (self-contained case study)

# optional · COMPOSIO ADAPTER (not required to reproduce; needs COMPOSIO_API_KEY)
python3 pipeline/composio_runner.py                  # dry-runs offline via MCP tools/list passthrough
```

## Repo layout

| Path | What it is |
|---|---|
| `apps.json` | The 100-app registry + schema/enum definitions (the assignment's research set). |
| `pipeline/agent.py` | 4-stage research agent orchestrator (DISCOVER → RESEARCH → NORMALIZE → EMIT) + schema validator + live per-app re-research. |
| `pipeline/verify.py` | Verification loop: evidence URL live-checks, claim keyword-corroboration, MCP endpoint probes, ground-truth scoring. |
| `pipeline/apply_corrections.py` | Applies the human adjudication ledger (`data/corrections.json`) → `data/final_research.json`. Diffable by design. |
| `pipeline/analyze.py` | Pattern mining → `reports/analysis.json` (auth mix, access×category, blocker taxonomy, easy-win/outreach/blocked queues). |
| `pipeline/build_site.py` | Renders `site/index.html` (single-file case study + embedded JSON dataset + JSON-LD). |
| `pipeline/composio_runner.py` | **Composio adapter (not run in this submission):** search + browser toolkits for the RESEARCH stage, plus offline official-MCP passthrough. |
| `data/pass1_research.json` | **Baseline** research output (LLM + targeted web searches). Preserved unedited so the loops' gains are measurable. |
| `data/final_research.json` | Post-verification dataset (pass 1 + 71 reviewed corrections across 2 rounds). The shipped answer key. |
| `data/ground_truth.json` | Human-adjudicated ground truth for the 40-app audit sample, with citations + scoring rules. |
| `data/corrections.json` | Every human decision with reason + citation; 6 pre-registered rules (R1–R6). |
| `data/verification_log.json` | Full verification narrative: loops A/B/C/D, misses taxonomy, agreement numbers, human touchpoints. |
| `reports/` | Verification runs (40-app + full-set) + accuracy scores + analysis. |
| `site/index.html` | **The deliverable.** Self-contained case study page. |

## What we actually used vs. what is a Composio adapter

**Actually used to produce this submission:** an LLM research agent with web-search + page-fetch tools (41 searches);
this repo's pipeline (351 live docs fetches, keyword corroboration, 11 manual JSON-RPC MCP probes); two human
adjudication rounds (71 logged decisions). The assignment said no paid accounts were needed.

**Implemented as a Composio adapter, not run here:** `pipeline/composio_runner.py` routes RESEARCH through Composio
toolkits (search + browser toolkits — the latter would fix the SPA-gated docs class) when `COMPOSIO_API_KEY` is set.
Its offline half runs today: official-MCP passthrough (`tools/list`) against the 42 apps in this set that already
speak MCP.

## Method in one paragraph

RESEARCH ran on an LLM research agent with web-search and page-fetch tools (41 searches — biased toward
long-tail/low-confidence apps; knowledge digests for mainstream SaaS; every claim cited). The repo's scripts are
the runnable orchestration + verification layer around that stage and can re-run research live per app. Four
verification loops follow: **(A)** machine corroboration — fetch every cited URL, keyword-check claims, probe MCP
endpoints; **(B)** cross-examination — adversarial first-party searches + manual JSON-RPC probes; **(C)** human
adjudication — every flag reviewed, every fix logged in `data/corrections.json` with a reason; **(D)** full-set
sweep — the same checks across all 100 rows (this loop found 5 more row errors and 20 dead links in the un-audited
60). The audit sample is 30 stratified + 10 blind holdout apps (195 scored field checks; Paygent Connect declared
unscorable — no observable docs exist). Numbers below are **agreement with docs-adjudicated ground truth on audited
checks** — not a blanket accuracy claim. Details and the honest error list live in the case study, section 04.

## Honesty notes (ask me about all of these in the interview)

- Errors we caught and kept on the page: phantom OAuth2 (Pylon, and again on Plain in the sweep), 3 over-listings
  (Freshdesk, Gladly, iPayX), 1 auth misfamily (Neo4j), 1 MCP under-claim (Pumble), 1 phantom official MCP
  (Discord), 1 under-listed auth (Brex), 1 more MCP under-claim (MrScraper), and 29 dead evidence links across the
  two rounds.
- Apps that defeated the agent: **Paygent Connect** (no discoverable developer docs — NMI white-label reseller).
  **NotebookLM** has no API at all (the "Enterprise API" hint is Gemini). Sherlock & Mermaid CLI are local tools —
  they belong in a skills/CLI bucket, not a hosted toolkit catalog.
- The machine flagger has low precision on SPA-gated docs (35 of 41 flags in round A were fetch limitations, not
  errors) — which is why the human loop is the last mile, not optional.
- Re-scoring the audit set after fixing it is partly by-construction; the blind holdout (50/50 in both passes) is
  the overfit guard — and the full-set sweep still found errors the audit hadn't sampled, which is the strongest
  argument for sweep > sample. Residual risk is listed on the page.
