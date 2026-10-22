# HLD and LLD: Autonomous Multi-Agent Research System

**Working title:** Cortex Lab **Version:** 0.1, build kickoff draft **Date:** 20 October 2026 **Companion doc:** PRD (requirement IDs such as FR-DS-4 refer to it) **Core stack:** React + Vite (TypeScript), FastAPI (Python 3.11+), LangGraph

Library APIs move fast. Pin versions in week 1 and check each snippet below against the pinned release. Code here is a design skeleton, not copy-paste final.

# Part A: High-Level Design (HLD)

## 1. Purpose and scope

This document describes how to build the system defined in the PRD: two input modes (Problem, Topic Discovery), a shared multi-agent research pipeline, human checkpoints, live streaming, persistence, and a backtest harness.

In scope: web app, API, agent orchestration, tools, storage, deployment. Out of scope for v1: multi-tenant org features, wet-lab integrations.

## 2. Architecture overview

```
+---------------------+        REST + SSE         +----------------------------+
|  React + Vite SPA   | <------------------------> |  FastAPI (API process)     |
|  - New run          |                            |  - auth, runs, state, SSE  |
|  - Live run view    |                            |  - enqueues jobs           |
|  - Checkpoints      |                            +------+---------------+-----+
|  - Report, backtest |                                   |               |
+---------------------+                       enqueue job  |               | read
                                                          v               v
                                                  +---------------+   +-----------------+
                                                  |  Redis        |   |  PostgreSQL     |
                                                  |  - job queue  |   |  - app tables   |
                                                  |  - pub/sub    |   |  - run_events   |
                                                  +-------+-------+   |  - LangGraph    |
                                                          |           |    checkpoints  |
                                                          v           |  - pgvector     |
                                             +--------------------------+  memory      |
                                             |  Worker process (arq)    |<-------------+
                                             |  LangGraph runtime       |
                                             |  - top graph + subgraphs |
                                             |  - event emitter         |
                                             |  - state projector       |
                                             +----+----------+----------+
                                                  |          |
                                    +-------------+--+   +---+-------------------+
                                    | LLM providers  |   | Tools                 |
                                    | (per-role cfg) |   | web, arXiv, S2,       |
                                    +----------------+   | OpenAlex, GitHub,     |
                                                         | fetcher, verifier,    |
                                                         | code sandbox          |
                                                         +-----------------------+
```

Key idea: the **API never runs the graph**. Long research runs execute in a **worker**. Everything the UI needs flows through **events stored in Postgres** and a **projection of graph state into normal tables**, so the UI is fast, replayable and survives restarts.

## 3. Components and responsibilities

| Component | Responsibility |
| --- | --- |
| **SPA (React + Vite)** | Run creation, live progress, panel transcript, problem board, lineage and idea views, checkpoint dialogs, report |
| **API (FastAPI)** | Auth, CRUD for runs, SSE event stream, accept checkpoint decisions, enqueue start and resume jobs, serve reports |
| **Worker (arq)** | Executes LangGraph runs, streams updates, enforces budgets, handles cancel and pause |
| **LangGraph runtime** | Top-level graph, discovery subgraph, research subgraph, debate loop, interrupts, fan-out |
| **Event emitter** | Writes each event to `run_events` and notifies Redis |
| **State projector** | Turns graph state updates into rows (evidence, ideas, lineage, problems) |
| **Tool layer** | Uniform interface over search, fetch, verify, sandbox, with caching and rate limits |
| **LLM factory** | Resolves a role (for example skeptic) to a configured model |
| **PostgreSQL** | App data, events, LangGraph checkpoints, pgvector memory |
| **Redis** | Job queue, pub/sub wake-ups, tool cache, cancel flags |
| **Sandbox** | Isolated container for experiment code (phase 5) |

## 4. Technology choices

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React 18, Vite, TypeScript, React Router | Fixed by requirement |
| UI | Tailwind plus shadcn/ui; React Flow for lineage graph; react-markdown for reports | Fast to build, graph view needs a real graph library |
| Client state | TanStack Query (REST), Zustand (live run state) | Server state and stream state have different lifecycles |
| Streaming | SSE using @microsoft/fetch-event-source | Native EventSource cannot send auth headers; this library also handles reconnect with last event id |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 (async) with Alembic | Fixed by requirement; typed models shared with LangGraph |
| Orchestration | LangGraph with AsyncPostgresSaver checkpointer | Fixed by requirement; durable state, interrupts, subgraphs, fan-out |
| LLM access | LangChain chat models via init\_chat\_model, role-to-model map in config | Provider swap without code change; different model for skeptic |
| Queue | arq (asyncio, Redis) | Fits an async FastAPI codebase, light to operate |
| Database | PostgreSQL 16 plus pgvector | One store for app data, checkpoints and vectors |
| Lineage graph | Postgres node and edge tables in v1 | Avoids running Neo4j on day one; revisit if graph queries get heavy |
| Web search | One pluggable provider (Tavily, Brave or Serper; pick in week 1) | Decision pending in PRD open questions |
| Scholarly | arXiv, Semantic Scholar, OpenAlex, GitHub APIs | Primary sources for evidence |
| Sandbox | Docker with no network, CPU and memory limits | Safe code execution for L3 validation |
| Observability | OpenTelemetry plus structured logs; LangSmith optional | Trace every agent step and tool call |
| Packaging | docker compose | One-command local and single-VM deploy |

## 5. LangGraph topology

### 5.1 Top-level graph

```
START -> classify_intake --(ambiguous)--> clarify (interrupt) --+
              |                                                  |
              +--(topic)--> [DISCOVERY subgraph] -> select_problems (interrupt)
              |                                                  |
              +--(problem)--------------------------------+      |
                                                          v      v
                                                      pick_next_problem <---------+
                                                          |                       |
                                                          v                       |
                                                   [RESEARCH subgraph]            |
                                                          |                       |
                                                   collect_result ----(more)------+
                                                          |
                                                       (done)
                                                          v
                                                   finalize_report -> END
```

### 5.2 Discovery subgraph (Topic mode, FR-DS-1 to FR-DS-6)

```
scope_topic -> plan_scans -> [landscape_scout x N, parallel via Send]
   -> mine_pain_points -> panel_round -> moderator --(not converged and rounds left)--> panel_round
                                                |
                                           (converged or limit)
                                                v
                                       synthesize_problems -> END
```

- **Scouts** run per source type (papers, preprints, repos and issues, forums, news, benchmarks, industry reports).
- **Panel round**: all persona agents speak concurrently, each reading the evidence digest and the transcript so far, each required to cite evidence ids. The **moderator** summarizes the round, scores convergence and lists unresolved disagreements.
- **Synthesize**: produces ranked ProblemCandidate objects (severity, tractability, gap size) with evidence.

### 5.3 Research subgraph (shared by both modes, FR-RS-1 to FR-RS-9)

```
frame_problem -> abstract_problem -> [literature_scout x N by subtopic, parallel]
  -> historian -> gap_analyst -> checkpoint_gaps (interrupt)
  -> [ideator x operators, parallel] -> analogist
  -> debate loop: skeptic -> novelty_checker -> judge --(revise and rounds left)--> ideator_revise -> skeptic
  -> evidence_grader -> validate -> ranker -> checkpoint_shortlist (interrupt)
  -> synthesize_report -> END
```

### 5.4 Design decisions

1. **One shared RunState schema** across top graph and subgraphs, so subgraphs plug in as nodes with no state mapping.
2. **Reducers on every list field** (append, or merge by id) so parallel Send branches never overwrite each other.
3. **Interrupts** (`interrupt()` plus `Command(resume=...)`) implement every human checkpoint. Nodes that call interrupt must be safe to re-run from the top on resume, because LangGraph re-executes the node.
4. **Problems run one at a time in v1** (loop through pick\_next\_problem). Parallel research per problem becomes child runs later.
5. **Budget and cancel checks** happen at node boundaries through a shared node wrapper.
6. **Custom events** use the LangGraph stream writer inside nodes, so the UI can show panel turns and tool calls as they happen.

## 6. Shared state (blackboard)

Every agent reads and writes one structured state, not chat messages:

| Area | Contents |
| --- | --- |
| Run | run\_id, mode, limits, spend, round counters |
| Discovery | scope, pain points, panel transcript, problem candidates, selected problems |
| Research | frame, abstract form, evidence store, lineage edges, gaps, ideas, critiques, validation results |
| Output | ranked ideas, report |

Rule: a claim without an evidence id must carry status hypothesis.

## 7. Data architecture

| Store | What lives there |
| --- | --- |
| LangGraph checkpoint tables (created by the checkpointer setup) | Full graph state per step, used for resume, pause and time travel |
| App tables (projections) | runs, run\_events, evidence, problem\_candidates, lineage nodes and edges, ideas, reports, checkpoints (human) |
| pgvector memory table | Embedded evidence and idea summaries for cross-session retrieval (FR-MM-2) |
| Redis | arq queue, pub/sub channel per run, tool result cache, cancel flags |

Projection means the UI queries simple tables instead of deserializing checkpoints.

## 8. Runtime flows

**8.1 Start run.** SPA posts the input. API creates a run row and enqueues start\_run. Worker builds initial state and streams the graph. Every update becomes events and projected rows.

**8.2 Live streaming.** Worker writes each event to `run_events` (monotonic seq) and publishes a wake-up on Redis. The SSE endpoint reads backlog after Last-Event-ID, then waits for wake-ups. A reconnecting client replays missed events exactly.

**8.3 Human checkpoint.** A node calls interrupt with a payload. The worker sees the interrupt chunk, writes a checkpoint.requested event, sets status awaiting\_input and exits. The user decides in the UI, the API validates and enqueues resume\_run with the decision, and the worker resumes with Command(resume=decision).

**8.4 Failure and resume.** State is checkpointed after every step. If a worker dies, a recovery job re-enqueues the run and resumes from the last checkpoint. Tool failures retry with backoff, then the node degrades (for example, continue with fewer sources and record a warning event).

**8.5 Cancel and pause.** The API sets a Redis flag. The node wrapper checks it at the next node boundary and stops cleanly. Pause is cancel with status paused; resume continues from the checkpoint.

## 9. Cross-cutting concerns

**Security.** JWT auth; every query filtered by user\_id; secrets only on server; sandbox with no network and hard CPU, memory and time limits; page fetcher blocks private and link-local IP ranges (SSRF).

**Prompt injection from the web.** Retrieved text is data, never instructions. Wrap it in delimited blocks, tell agents to ignore instructions inside it, give search-facing agents no privileged tools, and validate all outputs against Pydantic schemas.

**Cost control.** A usage callback records tokens and cost per call into state. The node wrapper stops the run gracefully when spend reaches the user limit. Cheap models handle scouting and extraction; strong models handle framing, ideation and judging.

**Observability.** Every agent step and tool call emits an event and an OpenTelemetry span with run\_id, node, model, tokens and latency.

**Scaling.** API scales horizontally (stateless). Workers scale by count; one run is pinned to one worker at a time via the queue. Postgres connection pools are sized per process.

## 10. Deployment (v1)

docker compose services: **web** (Vite build served by nginx), **api** (uvicorn), **worker** (arq), **postgres** (pgvector image), **redis**, optional **sandbox-runner**. Environment variables: DATABASE\_URL, REDIS\_URL, JWT\_SECRET, SEARCH\_PROVIDER and key, per-provider LLM keys, MODEL\_MAP path, DEFAULT\_BUDGET\_USD.

# Part B: Low-Level Design (LLD)

## 11. Repository layout

```
cortex-lab/
  docker-compose.yml
  backend/
    pyproject.toml
    alembic/
    app/
      main.py                 # FastAPI app factory
      config.py               # settings (pydantic-settings)
      auth/                   # JWT, password hashing, deps
      api/                    # routers: runs, auth, backtests, health
      db/                     # engine, models, repos
      events/                 # emitter, schemas, projector
      llm/                    # factory, usage callback
      tools/                  # search, scholarly, fetch, verify, sandbox
      graph/
        state.py              # RunState and domain models
        node.py               # agent_node wrapper
        top.py                # top-level graph
        discovery.py          # discovery subgraph
        research.py           # research subgraph
        agents/               # one module per agent (prompt plus logic)
        prompts/              # prompt templates
      worker/                 # arq functions: start_run, resume_run
      backtest/               # cases, runner, scoring
    tests/
  frontend/
    package.json  vite.config.ts
    src/
      app/  pages/  features/runs/  features/backtest/  lib/
  config/
    models.yaml               # role to model map
    domain_packs/             # per-domain tools and validators
```

## 12. Configuration and LLM factory

Never hardcode model ids in code. Map roles to models in `config/models.yaml`:

```yaml
roles:
  fast:      { model: 'PROVIDER_A:small-model',  temperature: 0.2 }   # scouts, extraction
  reason:    { model: 'PROVIDER_A:large-model',  temperature: 0.4 }   # framer, ideators, judge
  creative:  { model: 'PROVIDER_A:large-model',  temperature: 0.9 }   # ideators, panel personas
  critic:    { model: 'PROVIDER_B:large-model',  temperature: 0.2 }   # skeptic, novelty (different vendor on purpose)
agents:
  skeptic: critic
  novelty_checker: critic
  ideator: creative
  landscape_scout: fast
  # unlisted agents default to reason
```

```python
# app/llm/factory.py
from functools import lru_cache
from langchain.chat_models import init_chat_model
from app.config import models_cfg

@lru_cache
def get_llm(agent: str):
    role = models_cfg.agents.get(agent, 'reason')
    spec = models_cfg.roles[role]
    return init_chat_model(spec.model, temperature=spec.temperature)

def structured(agent: str, schema):
    return get_llm(agent).with_structured_output(schema)
```

Every agent returns a **Pydantic schema** through structured output. Free-text answers are only allowed in report prose.

## 13. State schemas

```python
# app/graph/state.py
import operator
from typing import Annotated, Literal, TypedDict
from pydantic import BaseModel, Field

def merge_by_id(left: list, right: list) -> list:
    out = {x.id: x for x in (left or [])}
    for x in (right or []):
        out[x.id] = x            # later write wins; lets agents update an idea
    return list(out.values())

def merge_spend(left: dict, right: dict) -> dict:
    out = dict(left or {})
    for k, v in (right or {}).items():
        out[k] = out.get(k, 0) + v
    return out

class Evidence(BaseModel):
    id: str
    claim: str
    source_url: str
    source_type: Literal['paper', 'preprint', 'repo', 'forum', 'news', 'blog', 'report', 'benchmark']
    quality: Literal['A', 'B', 'C', 'D'] = 'C'     # set by evidence_grader
    verified: bool = False                          # citation resolves and supports claim
    published: str | None = None

class PainPoint(BaseModel):
    id: str
    text: str
    cluster: str | None = None
    evidence_ids: list[str]

class PanelTurn(BaseModel):
    round: int
    persona: str
    position: str
    cites: list[str]                                # evidence ids; empty means opinion
    challenges: list[str] = []                      # persona ids being challenged

class ProblemCandidate(BaseModel):
    id: str
    statement: str
    why_it_matters: str
    evidence_ids: list[str]
    severity: float = Field(ge=0, le=1)
    tractability: float = Field(ge=0, le=1)
    gap_size: float = Field(ge=0, le=1)
    rank: int | None = None

class LineageEdge(BaseModel):
    id: str
    problem: str
    method: str
    limitation: str
    successor: str | None = None
    evidence_ids: list[str]

class Gap(BaseModel):
    id: str
    description: str
    kind: Literal['unsolved_case', 'weak_assumption', 'hidden_cost', 'untested_combo']
    evidence_ids: list[str]

class Critique(BaseModel):
    by: Literal['skeptic', 'novelty', 'judge']
    text: str
    severity: Literal['minor', 'major', 'fatal']
    prior_art_urls: list[str] = []

class Idea(BaseModel):
    id: str
    title: str
    operator: Literal['relax_assumption', 'transfer', 'combine', 'invert', 'resolve_bottleneck']
    description: str
    targets: str                                    # id of the limitation or gap it addresses
    evidence_ids: list[str] = []
    status: Literal['proposed', 'challenged', 'killed', 'validated', 'shortlisted'] = 'proposed'
    critiques: list[Critique] = []
    novelty: float | None = None
    feasibility: float | None = None
    impact: float | None = None
    validation_level: Literal['L0', 'L1', 'L2', 'L3'] = 'L0'
    next_test: str | None = None
    kill_reason: str | None = None

class Limits(BaseModel):
    depth: Literal['quick', 'standard', 'deep'] = 'standard'
    max_usd: float = 5.0
    max_debate_rounds: int = 2
    max_panel_rounds: int = 3
    max_wall_seconds: int = 3600

class RunState(TypedDict, total=False):
    run_id: str
    user_id: str
    raw_input: str
    mode: Literal['problem', 'topic']
    limits: Limits
    spend: Annotated[dict, merge_spend]             # {'usd': .., 'tokens': ..}
    warnings: Annotated[list[str], operator.add]
    # discovery
    scope: dict
    pain_points: Annotated[list[PainPoint], merge_by_id]
    transcript: Annotated[list[PanelTurn], operator.add]
    panel_round: int
    convergence: float
    problem_candidates: list[ProblemCandidate]
    selected_problem_ids: list[str]
    queue: list[str]                                # problems still to research
    current_problem: str | None
    # research
    frame: dict
    abstract_form: str
    evidence: Annotated[list[Evidence], merge_by_id]
    lineage: Annotated[list[LineageEdge], merge_by_id]
    gaps: Annotated[list[Gap], merge_by_id]
    ideas: Annotated[list[Idea], merge_by_id]
    debate_round: int
    results: Annotated[list[dict], operator.add]    # one entry per researched problem
    report: dict
```

## 14. Tool layer

One interface, many implementations, so agents never touch vendor SDKs.

```python
# app/tools/base.py
from typing import Protocol
from pydantic import BaseModel

class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str
    published: str | None = None
    score: float | None = None

class SearchTool(Protocol):
    name: str
    async def search(self, query: str, *, limit: int = 10, before: str | None = None) -> list[SearchHit]: ...
```

The `before` date filter is what makes backtesting possible (section 26).

| Tool | Purpose | Notes |
| --- | --- | --- |
| WebSearch | General web, news, forums | Provider chosen by config; results graded by domain quality |
| ArxivSearch | Preprints | Official API; supports date ranges |
| SemanticScholarSearch | Papers, citations, limitations text | Use the citation graph to find successors |
| OpenAlexSearch | Broad scholarly coverage | Good for date filtering and concept tags |
| GitHubSearch | Repos, issues, discussions | Source of real-world pain points |
| PageFetcher | Fetch and extract main text | httpx plus an article extractor; SSRF guard; size and time limits |
| CitationVerifier | Does the URL resolve and does the page support the claim | Used by evidence\_grader and again before final report |
| CodeSandbox | Run experiment code | Docker, no network, resource limits (phase 5) |

All tools go through a wrapper that adds: Redis cache (key = tool plus normalized query, TTL by tool), per-provider rate limiting, retry with exponential backoff, and a tool.call event.

## 15. Agent node catalog

Model tier refers to section 12. Every agent writes through the state reducers and emits events.

| Agent (node) | Reads | Writes | Tools | Tier |
| --- | --- | --- | --- | --- |
| classify\_intake | raw\_input | mode, clarifying questions | none | fast |
| scope\_topic | raw\_input | scope (subtopics, keywords, boundaries) | none | reason |
| landscape\_scout (xN) | scope, source type | evidence, raw findings | web, scholarly, GitHub, fetch | fast |
| mine\_pain\_points | evidence | pain\_points (clustered) | none | reason |
| panel personas (x5) | pain\_points, evidence digest, transcript | transcript turns | optional single follow-up search | creative |
| moderator | transcript | convergence, unresolved list | none | reason |
| synthesize\_problems | pain\_points, transcript | problem\_candidates (ranked) | none | reason |
| frame\_problem | problem statement | frame (root problem, constraints, metrics, subtopics) | none | reason |
| abstract\_problem | frame | abstract\_form (domain-free structure) | none | reason |
| literature\_scout (xN) | frame, subtopic | evidence | scholarly, web, fetch | fast |
| historian | evidence | lineage edges | semantic scholar citations | reason |
| gap\_analyst | lineage, evidence | gaps | none | reason |
| ideator (x operators) | gaps, lineage, operator | ideas | none | creative |
| analogist | abstract\_form | ideas (operator: transfer) | cross-field search | creative |
| skeptic | ideas | critiques | optional search | critic |
| novelty\_checker | ideas | critiques with prior art, novelty score | web, scholarly (independent queries) | critic |
| judge | ideas, critiques | scores, revise or stop decision | none | critic |
| evidence\_grader | evidence, ideas | quality, verified flags | fetch, verifier | fast |
| validate | ideas | validation\_level, next\_test | sandbox (phase 5) | reason |
| ranker | ideas | ranked shortlist | none | reason |
| synthesize\_report | everything | report | none | reason |
