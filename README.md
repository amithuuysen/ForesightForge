# ForesightForge

ForesightForge is an autonomous research council for deep technology. It accepts either a
**problem** you are blocked by or a **topic** you want to explore, and returns ranked,
evidence-backed directions to work on — with the lineage of how the field got stuck, the
evidence behind every claim, and the cheapest next test for each idea.

It uses FastAPI and LangGraph for the API and workflow, Neo4j for provenance, and React with
Vite for the operator console.

---

## Start locally

1. Run `npm --prefix frontend install` once to install the UI dependencies on the host.
2. Copy `.env.example` to `.env` and add a model provider key (see **Model providers**).
3. Start the services with `docker compose up --build`.
4. Open the operator console at `http://localhost:5173`; the API health check is at
   `http://localhost:8000/api/health` and Neo4j Browser is at `http://localhost:7474`.

The Compose defaults are for local development only. Do not reuse the default Neo4j password
outside a local machine.

---

## Two input modes

### Problem mode

You describe a bottleneck, a failure, or a constraint. The council frames it, reconstructs the
system from first principles, gathers prior art, attacks its own diagnosis, cross-examines,
invents, validates, and ranks.

### Topic Discovery mode

You only have a curiosity. The council discovers the problems worth solving **before** any
research happens, then hands your chosen problems to the same pipeline.

| Stage | What happens |
| --- | --- |
| `D1` Scope topic | clarifies the topic, sets boundaries, generates sub-topics and search vocabulary |
| `D2` Landscape scan | parallel web search across several source types and angles |
| `D3` Pain-point mining | extracts stated limitations, open problems and failure cases, with citations |
| `D4` Panel discussion | five personas plus a moderator debate over multiple rounds, scored for convergence |
| `D5` Problem synthesis | ranked problem statements with severity, tractability and gap size |
| `D6` You decide | human checkpoint: select, edit, merge or reject the problems |

> The `D4` panel is Practitioner, Academic, Strategist, Contrarian and Futurist. Each persona
> has its own mandate and stance vocabulary, and every statement carries the evidence ids it
> relied on. The Contrarian challenges; the Academic defends; the Practitioner reports from
> operating reality; the Futurist raises what the current framing misses.

**Auto-detect** is the default intake: the classifier reads your input and picks the mode. An
ambiguous input asks at most two clarifying questions and then proceeds on a stated assumption.

---

## The council pipeline

| Stage | Agent | Output |
| --- | --- | --- |
| `intake` | Intake Classifier | problem / topic / ambiguous, plus clarifying questions |
| `plan` | Principal Investigator | research plan, objectives, parallel subagent tasks |
| `deconstruct` | Architecture & Diagnostics Fellow | base architecture, governing equation, primitives, isolated flaw hotspot |
| `gather` | Research Fellows | real prior art and evidence from the public web, with reasoning traces |
| `attack` | Adversarial Red-Team | stress test of the diagnosis and its critical vulnerability |
| `cross_examine` | Council | deliberation turns and recorded disagreements |
| `refine_attempt` | Council | contested points re-investigated until convergence |
| `cross-pollinate` | Cross-Domain Invention Fellow | breakthrough inventions with laboratory protocols and expected gain |
| `project` | Quantitative Forecaster | metric trajectory and forecast |
| `synthesize` | Principal Investigator | the architectural invention blueprint |
| `cite` | Prior Art Auditor | passage-level citation verification |
| `verify` | Scientific Rigour Judge | rubric scorecard and verdict, then the evidence gate |
| `validate` | Scientific Rigour Judge | validation level per idea, then the feasibility/impact/novelty ranking |

---

## Workspaces

1. **Round Table** — the live run surface. Stage rail on the left, the roundtable in the centre
   with live speaking state, convergence dial and challenge/support flows, and the working
   channel on the right with the reasoning trace, the discussion thread and a steer box. A
   running budget meter and pause/cancel controls sit in the header.
2. **Council Chamber** — the post-run deliberation view: spotlight on the active fellow, council
   gallery with speaking state, the deliberation log, and a box to intervene with guidance.
3. **Agent Matrix** — the council plus a role rail that routes you to the work each agent owns.
4. **R&D Brief** — the deliverable: panel transcript, invention blueprint, base core architecture
   deconstruction, governing equation, primitives grid, root-cause flaw hotspot, flaw-versus-fix
   comparison, **ranked idea board** (what / why it should work / what it addresses / evidence /
   risks / validation level / cheapest next test), **discovered problems** with severity,
   tractability and gap size, prior art grounding, rigour scorecard, and the **run ledger**
   (intake mode, depth, budget, tokens, convergence, panel rounds), plus your own verified
   claims and open questions.
5. **Evidence Vault** — candidate sources with review status, extraction fidelity, date
   freshness, keyword search, sorting, and one-click claim creation from a passage.
6. **Observability** — the recorded path of a run: stage ribbon, event beats, and a replay
   control that walks the stored timeline.

---

## Model providers and role routing

The council needs a model. Providers are auto-detected in the order
NVIDIA → Anthropic → Gemini → Groq → OpenAI → custom, or forced with `LLM_PROVIDER`.
You can also pick a provider, model and key per request from the UI.

Model ids are never hardcoded. Roles resolve to a tier, and tiers resolve to a provider and
model through [`config/models.yaml`](config/models.yaml):

| Tier | Temperature | Used by |
| --- | --- | --- |
| `fast` | 0.2 | scouts, extraction, evidence grading, intake classification |
| `reason` | 0.4 | framing, gap analysis, judging, synthesis, ranking |
| `creative` | 0.9 | ideators, panel personas |
| `critic` | 0.2 | skeptic, novelty checker, judge |

A tier may pin a **different vendor** (`provider:model`), which is how the skeptic ends up on a
model that did not write the idea it is attacking. A pinned model overrides the per-request
provider; an empty model uses the request's provider.

**Degradation is honest.** Without a provider the pipeline still runs and still collects and
cites **real** web evidence. Model-derived stages are skipped and reported as
`provider_unavailable` rather than fabricated. Topic Discovery falls back to quoting real
limitation sentences from the retrieved pages, so the panel still debates cited evidence. Runs
end at `needs_evidence` until claims resolve to retrieved passages.

### Running against a local model

Ollama on the host works, but the API container cannot reach a loopback-bound service
directly. Bridge it once:

```bash
socat TCP-LISTEN:11435,fork,reuseaddr TCP:127.0.0.1:11434
```

Then point the container at the bridge in `.env`:

```
LLM_PROVIDER=ollama
MODEL_BASE_URL=http://172.18.0.1:11435/v1   # the Docker gateway
MODEL_NAME=minimax-m3.1-flash:cloud
MODEL_API_KEY=ollama-local
```

`docker compose up -d api` re-reads the env file. A plain `docker compose restart` does not.

> A local model is verbose. The stages that return a large structured document need a token
> budget of 8k or more, and the per-call timeout must be generous — a single call can take
> 30 to 100 seconds. The defaults in `.env.example` are sized for that.

---

## Run limits and cost

Every run carries its own limits and a running spend meter:

| Limit | Effect | Env override |
| --- | --- | --- |
| `depth` | `quick` / `standard` / `deep` — sets rounds, queries and sources | `DEFAULT_DEPTH` |
| `max_usd` | hard budget; the run stops calling models when it is spent | `DEFAULT_MAX_USD` |
| `max_rounds` | debate rounds | `DEPTH_*_ROUNDS` |
| `max_queries` / `max_sources` | search breadth | `DEPTH_*_QUERIES` / `DEPTH_*_SOURCES` |

A model call that **fails** is not charged, because it costs the provider nothing.

---

## Human checkpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /api/runs/{id}/checkpoint` | record a decision: approve, edit, reject, redirect, select, auto-select |
| `POST /api/runs/{id}/control` | pause, resume or cancel a run |

Topic mode always stops at the `D6` checkpoint with status `awaiting_input`. The research
pipeline stops at the shortlist checkpoint when `REQUIRE_HUMAN_CHECKPOINT` is enabled.

---

## Evidence integrity

The gather stage fans the question into public-web searches through DDGS, deduplicates results,
and fetches HTML pages for bounded main-text and publication-date extraction with Trafilatura.
Fetches are size- and time-bounded, reject non-public destinations and unsafe redirects, and
fall back to the search result snippet when a publisher blocks retrieval. Source records retain
their URL, originating query, publisher, retrieved text, retrieval timestamp, and publication
date when detectable.

Retrieved text is a candidate source, not a verified fact. A run only completes when every
claim resolves to a passage that exists in the retrieved set. No search API key is required.

---

## Configuration

All limits are environment-driven and documented in [.env.example](.env.example). Search bounds,
page-fetch bounds, discovery bounds, budget ceilings, subagent count, attempt count, convergence
threshold, model parameters and the citation requirement all live there. The defaults are read by
`backend/app/config.py`.

---

## Layout

```
backend/app/
  config.py     env-driven settings (search, workflow, discovery, budget)
  schemas.py    domain models and state reducers
  roles.py      persona roster and per-role model routing
  llm.py        provider registry and JSON-call helpers
  sources.py    multi-query web search and bounded page retrieval
  discovery.py  Topic Discovery subgraph (D1 to D5)
  workflow.py   the council pipeline (intake to validate)
  store.py      Neo4j persistence
  main.py       FastAPI app, SSE streaming, checkpoint and control endpoints
config/models.yaml   role to model map
frontend/src/
  components/RoundTable.tsx        live run surface
  components/ResearchOutcome.tsx   the R&D Brief
```

---

## Development checks

Frontend: `npm --prefix frontend run build` and `npm --prefix frontend run lint`.

Backend: from `backend/`, install `requirements.txt` in Python 3.12+, then run `pytest`.

See [docs/product-strategy.md](docs/product-strategy.md) for target users, product boundaries,
metrics, and the staged roadmap. The reusable ForesightForge UX skill is in
`.github/skills/foresightforge-product-ux/SKILL.md`. The product requirements this build
tracks live in [PRD.md](PRD.md) and the architecture in [HLD+LLD.md](HLD+LLD.md).
