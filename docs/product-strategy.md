# ForesightForge Product Strategy

## Product Thesis

ForesightForge helps research and strategy analysts build a reviewable, traceable starting point for a brief. Its differentiator is not autonomous certainty; it is preserving provenance and uncertainty as research moves from web pages toward decisions.

**Near-term promise:** A traceable starting point for research, with uncertainty and missing evidence kept visible.

## Positioning and Differentiation

Position ForesightForge as an **evidence collection and review workspace for decision research**, not as a general-purpose answer chatbot or an autonomous forecasting system.

Answer engines optimize for a quick response. Literature-discovery products optimize for academic papers. ForesightForge can earn a distinct position by making the research packet itself inspectable: which searches were run, what pages were actually retrieved, which results yielded readable text, which sources an analyst reviewed or excluded, and what remains unknown. Search infrastructure is replaceable; the durable product value is a trusted, reusable chain from question to source to reviewed evidence to decision brief.

Do not use “verified” to mean only that a claim has a source URL. Verification must test the specific evidence passage, preserve contradictory evidence, and expose human or model provenance.

## Initial User and Job

**Initial user:** An analyst at a small consulting, policy, or corporate strategy team who regularly prepares short landscape briefs.

**Job to be done:** When a topic changes or a decision is approaching, quickly collect relevant public sources, keep track of where each came from, and produce a reviewable evidence packet that can be turned into a defensible brief.

The first product should accelerate research intake and source review. It should not claim to independently forecast or debate until those capabilities exist and are evaluated.

## Current Product Reality

Working today:

- Create a research run from a domain and question.
- Fan out to up to three public-web searches and collect up to six unique HTML results.
- Fetch bounded pages, extract text and available metadata, and retain search snippets when extraction fails.
- Preserve source and query provenance in Neo4j and show workflow events.
- Search/filter the selected run's sources, open a source inspector, and mark a source reviewed or excluded in browser-local storage.
- Keep runs blocked when no source-linked claims exist.

Not yet implemented:

- Model-backed source analysis or agent debate.
- Claim extraction, passage-level citation, counterevidence analysis, or report synthesis.
- Server-synced analyst review annotations, notes, collaboration, monitoring, and export workflows. The current review state is local to the browser.
- A verification process that tests whether a source actually supports a claim. A source-ID link alone is not proof.

## Product Risks

1. **Expectation gap:** Agent roles and “debate” language can imply reasoning that the workflow does not perform.
2. **Weak verification semantics:** Citation presence must not be confused with claim support or truth.
3. **Retrieval coverage:** Public search providers can rate-limit or change; source fetching can fail; dates may be missing or inaccurate.
4. **Missing user outcome:** Analysts still need to synthesize sources themselves.
5. **Operational boundaries:** Local single-user behavior is not yet team-ready; long-running research should eventually be asynchronous and recoverable.

## Product Discovery and Go-to-Market

Start with five to eight research or strategy analysts who regularly produce short market, policy, or technology briefs. Observe the full job rather than asking whether they like a “multi-agent debate.” Ask for their last real brief, how they found and checked sources, where provenance was lost, what had to be updated later, and what they would trust a tool to automate.

Run a concierge pilot on ten real questions: use ForesightForge to collect the source packet, then watch analysts review it and finish their brief in their existing tools. Compare time-to-first-useful-source, source relevance, source review completion, snippet-only fallback rates, and whether the packet is reused in a delivered decision document. If analysts only value a generated answer, revisit the wedge; if they value source auditability, deepen the review and claim workflow before adding more agent personas.

### Business-Model Hypotheses

Treat these as experiments, not commitments:

- **Individual starter:** local or low-cost use for bounded investigations and personal source review.
- **Professional analyst:** paid higher run volume, saved research topics, reruns, change tracking, and cited exports.
- **Research team:** shared source libraries, review assignment, comments, approvals, and a common audit trail.
- **Enterprise/policy team:** data separation, retention controls, approved source domains, model/provider controls, access management, and integrations.

Do not charge for raw source count alone. Validate willingness to pay for repeat monitoring, collaboration, trusted provenance, and the time saved turning reviewed sources into a brief. Never monetize by hiding source limitations or weakening the evidence gate.

## Success Definition

**Proposed north-star metric:** Research packets reused in a real brief or decision per active analyst per month, where a packet includes reviewed sources and explicit open questions. This measures value beyond search volume and rewards careful uncertainty handling.

Pair it with guardrails: review completion, source-extraction success, proportion of cited claims with passage-level evidence, correction rate, retrieval failures, and analyst trust calibration. Do not optimize solely for faster runs, more citations, or more generated claims.

## Roadmap

### 1. Reviewable Research Intake

Make the current MVP useful and honest. The client now has an investigation brief, a scroll-linked view of query/page/review anatomy, a source inspector, extraction/freshness indicators, persistent browser-local reviewed/excluded states, filters, and a source collection audit. Next, move review states to the API/Neo4j, add analyst notes, improve result deduplication/quality cues, and make source retrieval resilient to slow or interrupted runs. Use clear failures and recoverable status.

**Exit condition:** A pilot analyst can collect, inspect, filter, and review a source packet without losing query provenance, and can identify snippet-only pages and unknown publication dates at a glance.

### 2. Evidence Curation

Add quality/relevance signals with visible rationale, date and source-type filters, duplicate clusters, analyst annotations, and explicit candidate/reviewed/excluded/disputed states. Keep a full source trail.

**Exit condition:** Analysts can explain why a source was kept, excluded, or disputed, and those decisions persist across devices and runs.

### 3. Human-Led Brief Builder

Let analysts select exact passages, turn them into claims, attach supporting and opposing sources, record confidence rationale and open questions, and export a cited brief. The human remains the author and verifier.

**Exit condition:** A reviewer can click from each brief claim to the exact supporting and opposing passages and see who reviewed them.

### 4. Reviewed Model Assistance

Add model-suggested summaries, claim candidates, contradiction detection, and alternative interpretations. Every suggestion must cite retrieved passages, show uncertainty and model provenance, and require analyst review. Evaluate extraction and citation fidelity before expanding automation.

**Exit condition:** On a human-reviewed evaluation set, model suggestions save time without increasing unsupported claims or hiding counterevidence.

### 5. Decision Workflows

Only after repeated usage validates demand, add saved topics, scheduled re-runs, change detection, alerts, collaboration, permissions, exports, and integrations. Build multi-user isolation and operational controls before selling team workflows.

**Exit condition:** Users return for changes to tracked questions, and shared review/export flows fit into their existing decision process.

## Product Metrics

- Time from question submission to first useful source.
- Share of runs with at least one analyst-reviewed source.
- Share of saved claims with passage-level supporting and counterevidence links.
- Source extraction success and snippet-only fallback rate.
- Duplicate rate and review exclusion rate.
- Percentage of runs reopened or reused in a later brief.
- User-reported time saved and trust calibration, not raw source count alone.

## UI Direction

Use a useful research work surface first, with cinematic storytelling as an explanation layer. The scroll story should reveal the anatomy of a real run: question, query variants, page retrieval, extracted text, and review status. Keep source filtering and reading stable; animate only meaningful state transitions. Provide reduced-motion behavior and keep all source metadata available without motion.
