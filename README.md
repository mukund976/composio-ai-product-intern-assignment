# appkit-research — 100-app toolkit research, built as an agent pipeline

**Take-home deliverable for Composio's AI Product Ops Intern role.** One agent pipeline researched 100 apps
(auth · self-serve vs gated · API surface · MCP · buildability · evidence), then machine + human verification
loops stress-tested the answers and measured accuracy honestly (96.9% → 100% on a 40-app audit; 9 dead
evidence links → 0).

**Start here:** `site/index.html` — the self-contained case study (open in any browser; no external assets).

---

## Run the chain (Python 3.10+, network required for steps 1–2)

```bash
pip install -r pipeline/requirements.txt

# 0 · schema-gate the dataset (100 rows, enum-validated)         ~0.1s
python3 pipeline/agent.py validate

# 1 · the verification loop against LIVE docs (the audit trigger) ~60s
python3 pipeline/verify.py check --pass data/pass1_research.json  --out reports/pass1_verification.json
python3 pipeline/verify.py check --pass data/final_research.json  --out reports/final_verification.json

# 2 · score any pass against human ground truth (reproduces the accuracy numbers)
python3 pipeline/verify.py score --pass data/pass1_research.json   # -> 189/195 = 96.9%
python3 pipeline/verify.py score --pass data/final_research.json   # -> 195/195 = 100%

# 3 · apply the reviewed corrections (human loop output)
python3 pipeline/apply_corrections.py

# 4 · mine the patterns + rebuild the case-study page
python3 pipeline/analyze.py
python3 pipeline/build_site.py           # -> site/index.html

# optional · route RESEARCH through Composio toolkits (needs COMPOSIO_API_KEY)
python3 pipeline/composio_runner.py      # dry-runs offline via MCP passthrough demo
```

Serve locally with `python3 -m http.server 8000 -d site` and open `http://localhost:8000`.

## Repo layout

| Path | What it is |
|---|---|
| `apps.json` | The 100-app registry + schema/enum definitions (the assignment's research set). |
| `pipeline/agent.py` | 4-stage research agent orchestrator (DISCOVER → RESEARCH → NORMALIZE → EMIT) + schema validator + live re-research of any app. |
| `pipeline/verify.py` | Verification loop: evidence URL live-checks, claim keyword-corroboration, MCP endpoint probes, ground-truth scoring. |
| `pipeline/apply_corrections.py` | Applies the human adjudication ledger (`data/corrections.json`) to produce the final dataset. Diffable by design. |
| `pipeline/analyze.py` | Pattern mining → `reports/analysis.json` (auth mix, access×category, blocker taxonomy, easy-win/outreach/blocked queues). |
| `pipeline/build_site.py` | Renders `site/index.html` (single-file case study + embedded JSON dataset + JSON-LD). |
| `pipeline/composio_runner.py` | Pluggable Composio SDK slot (search + browser toolkits, official-MCP passthrough). |
| `data/pass1_research.json` | **Baseline** research output (LLM + 21 targeted web searches). Preserved unedited so the loops' gains are measurable. |
| `data/final_research.json` | Post-verification dataset (pass 1 + 33 reviewed corrections). The shipped answer key. |
| `data/ground_truth.json` | Human-adjudicated ground truth for the 40-app audit sample, with citations + scoring rules. |
| `data/corrections.json` | Every human decision with reason + citation; 5 pre-registered rules (R1–R5). |
| `data/verification_log.json` | The full verification narrative: loops A/B/C, misses taxonomy, accuracy numbers, human touchpoints. |
| `reports/` | Verification run outputs + accuracy scores + analysis. |
| `site/index.html` | **The deliverable.** Self-contained case study page. |

## Method in one paragraph

RESEARCH ran on an LLM research agent with web-search and page-fetch tools (29 searches — biased toward
long-tail/low-confidence apps; knowledge digests for mainstream SaaS; every claim cited). The repo's scripts are
the runnable orchestration + verification layer around that stage and can re-run research live per app. Three
verification loops follow: **(A)** machine corroboration — fetch every cited URL, keyword-check claims, probe MCP
endpoints; **(B)** cross-examination — adversarial first-party searches + manual JSON-RPC probes; **(C)** human
adjudication — every flag reviewed, every fix logged in `data/corrections.json` with a reason. The audit sample is
30 stratified + 10 blind holdout apps (195 scored field checks; Paygent Connect declared unscorable — no observable
docs exist). Details and the honest error list live in the case study, section 04.

## Honesty notes (ask me about all of these in the interview)

- Pass-1 errors we caught: 1 phantom auth (Pylon), 3 over-listings, 1 auth misfamily (Neo4j), 1 MCP under-claim
  (Pumble), 9 dead evidence links, 2 name-collision traps (Consensus≠goConsensus, Pylon≠pylon.page).
- Apps that defeated the agent: **Paygent Connect** (no discoverable developer docs — NMI white-label reseller).
  **NotebookLM** has no API at all (the "Enterprise API" hint is Gemini). Sherlock & Mermaid CLI are local tools —
  they belong in a skills/CLI bucket, not a hosted toolkit catalog.
- The machine flagger has low precision on SPA-gated docs (35 of 41 flags were fetch limitations, not errors) —
  which is exactly why the human loop is the last mile, not optional.
- Re-scoring the audit set after fixing it is partly by-construction; the blind holdout (50/50 in both passes) is
  the overfit guard. Residual risk is listed on the page.
