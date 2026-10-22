# Product Requirements Document: Autonomous Multi-Agent Research System

**Working title:** Cortex Lab (placeholder, rename freely) **Version:** 0.1, build kickoff draft **Date:** 20 October 2026 **Owner:** \[Product owner\] **Stack (fixed):** React + Vite, FastAPI, LangGraph

## 1. Executive summary

Cortex Lab is a multi-agent research system that behaves like a research lab. A user gives it either a **problem** (for example, a bottleneck they are facing) or just a **topic** (for example, a field they want to explore). The system understands the core of the input, finds out what previous and current research has done, locates where existing solutions fall short, and proposes **new technologies, methods or enhancements** that address the real underlying problem. Every idea comes with evidence, risks, and the cheapest next test.

The key product bet is the **thinking pattern**, not the search. Breakthroughs usually come from understanding why the last generation of solutions stopped working, then changing one assumption. The system automates that chain of reasoning, across any domain.

A second bet, added at kickoff: users do not always arrive with a problem. In **Topic Discovery mode**, the system runs web search and a multi-stage autonomous discussion between specialist agents to find the problems worth solving, then hands the chosen ones to the research pipeline.

## 2. Problem and opportunity

**User problem.** Researchers, engineers and founders spend weeks on literature surveys and still miss cross-field ideas. Existing AI tools mostly summarize papers. They rarely invent, rarely test, and almost never help when the user only has a vague topic.

**Opportunity.** The AI-scientist category is real and funded, but current products are narrow in domain, closed, or stop at hypotheses (see section 5). A domain-agnostic, open, problem-first system with built-in validation and a trust benchmark is unclaimed.

## 3. Vision, goals and non-goals

**Vision.** Anyone can describe a pain point or a topic of curiosity and get what a small research team would produce in a week: a grounded map of the field, a diagnosis of why it is stuck, and a short list of credible new directions.

**Goals (v1)**

1. Accept a problem OR a topic, in plain language, in any domain.
2. Produce ranked, evidence-backed new ideas that target a specific known limitation.
3. Validate each idea with the cheapest feasible test and label how far it was validated.
4. Show the agents working (live), and let the human steer at defined checkpoints.
5. Prove quality with a repeatable backtest, not just demos.

**Non-goals (v1)**

- Running wet-lab or physical experiments.
- Replacing peer review or claiming guaranteed novelty. Output is a research lead, not a result.
- Writing full publishable papers (a structured report is enough).
- Multi-tenant enterprise features (SSO, billing, org admin). These come later.

## 4. Users and personas

| Persona | Context | What they need |
| --- | --- | --- |
| **Applied researcher / PhD student** | Knows the field, short on time | Fast survey, lineage of methods, gaps, novel angles to test |
| **Engineer / tech lead** | Has a concrete bottleneck | A root-cause view and credible alternative approaches |
| **Founder / strategist / curious generalist** | Has only a topic or an interest area | Discovery of the real open problems, then directions worth pursuing |

## 5. Competitive landscape and positioning

Competitor facts below come from public sources reviewed in October 2026. Re-verify before external use.

| Competitor | What it does well | Gap we target |
| --- | --- | --- |
| Google Co-Scientist | Multi-agent generate, debate, evolve loop; strong in biomedicine | Biomedical focus; generates hypotheses but does not run experiments |
| Edison Scientific Kosmos | Parallel agents plus a shared world model; cited reports; novelty (Precedent) agent | Closed, per-run pricing, focused on biology, chemistry, materials; starts from an objective plus dataset |
| Sakana AI Scientist | End-to-end experiments and paper writing | ML research only; paper-oriented |
| Deep-research tools (OpenAI, Gemini, Perplexity, Elicit and similar) | Search and cited synthesis | Summarize; do not invent or validate |

**Our differentiation**

1. **Domain-agnostic core** with pluggable domain packs.
2. **Problem-first AND topic-first.** Accepts a raw pain point, or discovers problems from a topic.
3. **Lineage-driven ideation.** Problem to method to limitation to successor, plus explicit idea operators and cross-domain analogy.
4. **Validation ladder.** Every idea is tested at the cheapest feasible level and labeled.
5. **Built-in backtest.** Replay a field before a known breakthrough and score rediscovery.
6. **Open and self-hostable**, bring-your-own-model.
7. **Persistent memory** so each session builds on earlier ones.

## 6. Product principles

1. **Evidence or it is a hypothesis.** Every claim carries a citation or is marked as a hypothesis.
2. **Adversarial by design.** Idea generators are always challenged by a separate skeptic, ideally on a different model.
3. **Transparent process.** The user can see what each agent did and why an idea survived or died.
4. **Human at the cheap-to-correct points.** Checkpoints sit where direction errors cost least.
5. **Bounded autonomy.** Every run has budget, round and time limits.

## 7. Input modes and user journeys

### Mode A: Problem mode

User enters a problem (for example, a performance bottleneck, a failure, a constraint). The system frames it, researches it and proposes new approaches.

### Mode B: Topic Discovery mode (new)

User enters only a topic or area. The system discovers the problems first.

| Stage | What happens |
| --- | --- |
| D1 Topic scoping | Clarifies the topic, sets boundaries, generates sub-topics and search vocabulary |
| D2 Landscape scan | Parallel scouts run web and scholarly search across papers, preprints, code repos and issues, forums, news, industry reports, benchmarks |
| D3 Pain-point mining | Extracts stated limitations, open problems, failure cases, future-work sections and recurring user complaints; clusters them |
| D4 Panel discussion | Several persona agents (practitioner, academic, industry strategist, contrarian, futurist) debate over multiple rounds, moderated, converging on what really matters |
| D5 Problem synthesis | Produces ranked problem statements with evidence, severity, tractability and gap size |
| D6 Human checkpoint | User picks, edits or merges problems (or allows auto-selection of the top N) |

Selected problems flow into the same research pipeline as Mode A.

### Shared research pipeline (both modes)

1. **Frame**: root problem, constraints, metrics; abstract it into domain-free terms.
2. **Survey**: parallel literature scouts plus a historian building the lineage.
3. **Gap analysis**: what is unsolved and why. Human checkpoint 1.
4. **Ideation**: ideators using idea operators plus a cross-domain analogist.
5. **Challenge**: skeptic and novelty checker debate loop with a judge.
6. **Validate**: experimenter runs the cheapest feasible test.
7. **Synthesize**: ranked report. Human checkpoint 2 on the shortlist.

## 8. Functional requirements

Priority: **P0** = required for MVP, **P1** = next, **P2** = later.

### 8.1 Intake

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-IN-1 | User can submit free-text input; system classifies it as problem, topic, or ambiguous | P0 |
| FR-IN-2 | For ambiguous input, system asks at most two clarifying questions, then proceeds with stated assumptions | P0 |
| FR-IN-3 | User can set run limits: budget, max rounds, depth (quick, standard, deep) | P0 |
| FR-IN-4 | User can attach context (links, text, PDFs) as seed material | P1 |
| FR-IN-5 | User can pick domain pack or let system auto-detect | P1 |

### 8.2 Topic Discovery

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-DS-1 | Scope the topic into sub-topics and keywords | P0 |
| FR-DS-2 | Run parallel web and scholarly search across multiple source types | P0 |
| FR-DS-3 | Extract and cluster pain points with source citations | P0 |
| FR-DS-4 | Run a multi-round autonomous panel discussion with at least four distinct personas and a moderator | P0 |
| FR-DS-5 | Output ranked problem statements with evidence, severity, tractability and gap size | P0 |
| FR-DS-6 | Checkpoint: user selects, edits, merges or rejects problems; option to auto-select top N | P0 |
| FR-DS-7 | Show the discussion transcript and which evidence supported each problem | P1 |
| FR-DS-8 | User can inject a comment mid-discussion to steer it | P2 |

### 8.3 Research pipeline

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-RS-1 | Problem Framer produces root problem, constraints, metrics, and an abstract structural form | P0 |
| FR-RS-2 | Parallel literature scouts search papers, code, benchmarks and the web, split by sub-topic | P0 |
| FR-RS-3 | Historian builds a lineage graph (problem, method, limitation, successor) | P0 |
| FR-RS-4 | Gap Analyst lists unsolved cases and weak assumptions, each with evidence | P0 |
| FR-RS-5 | Ideators generate ideas using explicit idea operators (relax assumption, transfer, combine, invert, resolve bottleneck) | P0 |
| FR-RS-6 | Cross-Domain Analogist proposes transfers from other fields with the same abstract structure | P1 |
| FR-RS-7 | Skeptic challenges ideas; Novelty Checker runs independent prior-art searches; judge scores each round | P0 |
| FR-RS-8 | Evidence Grader labels each claim by source quality and verifies that citations resolve | P0 |
| FR-RS-9 | Ranker scores surviving ideas on feasibility, impact, novelty and cost to test | P0 |

### 8.4 Validation

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-VL-1 | Each idea gets a validation level: L0 reasoning check, L1 evidence cross-check, L2 math or simulation, L3 sandboxed code experiment | P0 (L0, L1), P1 (L2, L3) |
| FR-VL-2 | Sandboxed code execution with resource and time limits | P1 |
| FR-VL-3 | Failed or killed ideas are kept with the reason | P0 |

### 8.5 Memory and knowledge

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-MM-1 | Persist every run: state, evidence, ideas, transcript | P0 |
| FR-MM-2 | Cross-session memory: new runs retrieve relevant earlier evidence and lineage | P1 |
| FR-MM-3 | User can pin or exclude evidence sources | P2 |

### 8.6 Output

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-OT-1 | Structured report: framing, landscape, lineage, gaps, ranked ideas, risks, next steps, citations | P0 |
| FR-OT-2 | Each idea shows: what, why it should work, which limitation it addresses, evidence, risks, validation level, cheapest next test | P0 |
| FR-OT-3 | Export to Markdown and PDF | P1 |
| FR-OT-4 | Lineage graph and idea board visualizations | P1 |

### 8.7 Live experience and human control

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-UX-1 | Live progress stream: which agent is active, what it found, running cost | P0 |
| FR-UX-2 | Human checkpoints (problem selection, post gap analysis, final shortlist) with approve, edit, redirect | P0 |
| FR-UX-3 | Pause, resume and cancel a run | P0 |
| FR-UX-4 | Run history and re-open past runs | P0 |
| FR-UX-5 | Fork a run from any checkpoint with changed assumptions | P2 |

### 8.8 Platform

| ID | Requirement | Pri |
| --- | --- | --- |
| FR-PF-1 | Configurable model per agent role (skeptic on a different model from ideators) | P0 |
| FR-PF-2 | Pluggable tool and domain packs | P1 |
| FR-PF-3 | Backtest harness to replay historical snapshots and score results | P0 |
| FR-PF-4 | Basic auth and per-user data isolation | P0 |

## 9. Agent roster (summary)

Full design is in the HLD+LLD document.

| Agent | Purpose |
| --- | --- |
| Orchestrator (PI) | Plans, routes, decides when to loop or stop |
| Intake Classifier | Problem, topic or ambiguous; clarifying questions |
| Topic Scoper, Landscape Scouts, Pain-Point Miner | Discovery stages D1 to D3 |
| Panel personas plus Moderator | Discovery stage D4 |
| Problem Synthesizer | Discovery stage D5 |
| Problem Framer and Abstractor | Root problem, constraints, abstract form |
| Literature Scouts, Historian, Gap Analyst | Survey and gap analysis |
| Ideators and Cross-Domain Analogist | Idea generation |
| Skeptic, Novelty Checker, Judge | Adversarial challenge |
| Evidence Grader | Claim and citation quality |
| Experimenter | Cheapest feasible validation |
| Ranker and Synthesizer | Final ranked report |

## 10. Non-functional requirements

| Area | Requirement |
| --- | --- |
| Performance | First live event within 5 seconds of run start; quick-depth run completes in under 10 minutes; standard under 30 minutes (targets, tune after first benchmarks) |
| Cost control | Hard per-run token and tool-call budget; user sees running cost; run stops gracefully at the limit |
| Reliability | Runs survive server restarts and resume from the last checkpoint; tool failures retry with backoff, then degrade gracefully |
| Trust | No uncited claim presented as fact; citation links verified before the report is finalized |
| Security | Auth required; per-user data isolation; sandboxed code execution with no outbound network by default; secrets never in client |
| Privacy | User inputs not used for training; delete-run support |
| Observability | Full trace of every agent step, tool call, cost and latency |
| Portability | Runs via docker compose; model provider swappable by configuration |

## 11. Success metrics and evaluation

### 11.1 Backtest benchmark (primary quality gate)

Build a set of known breakthroughs across at least four domains. For each, freeze the literature before the breakthrough, run the system, and measure:

- **Rediscovery rate**: does a top-5 idea match the real breakthrough in essence?
- **Gap accuracy**: did it identify the limitation that motivated the breakthrough?
- **Lineage accuracy**: does the lineage match the true history?

MVP target: rediscovery in at least 2 of 5 benchmark cases and gap accuracy above 60 percent. These are starting targets, adjust after the first run.

### 11.2 Output quality

- Citation validity: at least 98 percent of links resolve and support the claim (sampled review).
- Novelty precision: share of top ideas with no clear prior art found by an independent human check.
- Discovery quality (Mode B): share of surfaced problems that human experts rate as real and worth solving.

### 11.3 Product and operations

- Time to first useful output, cost per run, run completion rate.
- Checkpoint acceptance: how often users accept versus heavily edit proposals.
- User-rated usefulness of the top 3 ideas (1 to 5 scale).

## 12. MVP scope and roadmap

Durations are estimates for a small team and should be adjusted after the first sprint.

| Phase | Scope | Estimate |
| --- | --- | --- |
| **0. Foundations** | Repo, auth, DB, LangGraph skeleton with Postgres checkpointer, SSE streaming, basic UI shell | 1 to 2 weeks |
| **1. Problem mode core** | Framer, scouts, historian, gap analyst, ideators, synthesizer; checkpoint 1; report view | 3 to 4 weeks |
| **2. Adversarial loop** | Skeptic, novelty checker, judge, evidence grader; L0 and L1 validation; checkpoint 2 | 2 to 3 weeks |
| **3. Topic Discovery mode** | D1 to D6 subgraph, panel discussion, discovery UI, hand-off into research pipeline | 3 to 4 weeks |
| **4. Backtest harness** | Benchmark set, replay tooling, scoring dashboard; first quality report | 2 weeks (start in parallel with phase 2) |
| **5. Validation and memory** | Sandbox experimenter (L2, L3), cross-session memory, analogist, exports | 3 to 4 weeks |

**MVP = phases 0 to 4.** Phase 5 follows once the backtest shows the core loop works.

## 13. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Hallucinated papers and claims | Retrieval-grounded citations only; link verification; uncited claims labeled hypothesis |
| Fake novelty | Novelty Checker runs independent searches and never trusts the ideator |
| Agents agree with each other | Different prompt and different model for the skeptic; judge scores disagreement |
| Panel discussion becomes generic chatter | Distinct persona mandates, evidence required for each position, moderator forces convergence on ranked problems |
| Runaway cost or loops | Hard budgets, round caps, minimum-improvement stopping rule |
| Shallow surveys | Score scouts on key-paper coverage in the backtest |
| Web source quality (SEO noise, forums) | Source-quality grading; weight peer-reviewed and primary sources higher |
| Output over-trusted by users | Clear validation-level labels; report states what was and was not tested |
| Scope creep across domains | Ship one or two domain packs first; core stays domain-agnostic |

## 14. Assumptions and open questions

**Assumptions**

- Users accept runs of several minutes in exchange for depth, with live progress.
- Public search APIs (web, arXiv, Semantic Scholar, OpenAlex, GitHub) provide enough coverage for v1.
- At least one frontier model provider is available, with a second for the skeptic role.

**Open questions (decide in week 1)**

1. Initial domain packs: which one or two domains for the first benchmark and demo?
2. Which search provider for general web (cost, quality, terms of use)?
3. Auto-select top N problems in Topic mode, or always require a user pick?
4. Hosting target for v1: single VM with docker compose, or managed cloud?
5. Licensing: open-source the core from day one, or later?
6. Final product name.
