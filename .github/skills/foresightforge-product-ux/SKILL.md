---
name: foresightforge-product-ux
description: "Use when designing, reviewing, or implementing ForesightForge product UX, research workflows, evidence review, source provenance, scroll storytelling, or accessible motion."
---

# ForesightForge Product UX

Use this skill for product strategy and client-interface work in ForesightForge. Treat the running code as the authority for current capabilities; distinguish working behavior from roadmap ideas.

## Product Promise

ForesightForge is an evidence-first research workspace. Its current useful promise is: **a traceable starting point for research, with uncertainty and missing evidence kept visible**.

It now runs in two modes. **Problem mode** takes a specific bottleneck and drives a twelve-stage council: intake classification, planning, first-principles deconstruction, evidence gathering, adversarial attack, cross-examination, contested-point refinement, cross-domain invention, trajectory modelling, synthesis, citation verification, and rigour judging with idea ranking. **Topic Discovery mode** takes a curiosity and discovers the problems first: topic scoping, landscape scan, pain-point mining, a multi-round panel debate with a moderator, ranked problem synthesis, and a human checkpoint where the user chooses which problems to research.

Every stage degrades honestly. Without a model provider the run still collects, extracts and cites **real** web evidence; model-derived stages report `provider_unavailable` rather than fabricating, and Topic Discovery falls back to quoting real limitation sentences from retrieved pages so the panel still debates cited evidence.

## Design Workflow

1. Identify the user, decision, and job-to-be-done. The initial target is a research or strategy analyst preparing a short, defensible landscape brief.
2. Verify the actual API and data states before designing labels, metrics, animations, or controls.
3. Put the next useful action first: frame a question, collect sources, inspect provenance, review evidence, and record uncertainty.
4. Separate retrieved material, analyst-reviewed sources, proposed claims, counterevidence, and verified conclusions in both data and visual language.
5. Make controls real and persistent where the product supports them. Never use decorative controls that imply unavailable behavior.
6. Use scroll storytelling to clarify process or spatial relationships, not to disguise loading, fake a debate, or delay core workflows.
7. Validate desktop and narrow mobile layouts, keyboard operation, accessible names, focus behavior, and reduced-motion behavior.

## The Live Run Surface

The Round Table is the live-run view and follows the Cortex Lab reference layout: a stage rail on the left, the roundtable in the centre, the working channel on the right.

- **Stage rail** shows the pipeline as pending, active, done or checkpoint. Each step carries a real count (subtopics, sources, pain points, round number).
- **Roundtable** renders one seat per agent around a moderator dial. The dial shows real convergence against a target. The active speaker gets a halo and a live label. Challenge and support flows draw between seats only when a turn actually names a counterparty.
- **Working channel** shows the reasoning trace and tool calls as they happen, then the discussion thread with per-persona stance tags and evidence chips, and a steer box.
- **Header** carries the running budget meter, pause and cancel, and the mode badge.

Rules for this surface:
- Never animate a seat as speaking unless a real speech event produced it.
- Never draw a flow line between two agents without a recorded challenge.
- Never fill the discussion thread with placeholder dialogue when the council produced none. Show the empty state and say why.
- The budget meter reads from real spend. A failed model call is not charged, so the meter must not move for one.

## Evidence-First Information Architecture

Prefer these information zones:

- **Intake surface:** mode (auto-detect, problem, topic), domain, question, depth, budget, and model. The root path is the intake surface; an investigation path opens a run.
- **Round Table (live run):** stage rail, roundtable with convergence dial and speaking state, working channel with reasoning trace, discussion thread and steer box, budget meter, run controls.
- **Evidence desk:** source title, publisher, original URL, publication date when available, retrieval time, originating query, extraction status, review status, and analyst notes.
- **Synthesis workspace:** proposed claims with passage-level citations, support, counterevidence, confidence rationale, and unresolved questions. Only expose this as working functionality once implemented.
- **Ranked idea board:** per idea — what it is, why it should work, which limitation it addresses, its evidence, its risks, its validation level (L0 to L3) and its cheapest next test.
- **Discovered problems:** per problem — statement, why it matters, severity, tractability, gap size, and the evidence ids behind it.
- **Run ledger:** intake mode, depth, budget spent against the ceiling, model calls, tokens, convergence and panel rounds.
- **Run history and audit:** timestamped system actions and failures, not inferred agent dialogue.

## Validation Levels

Every idea carries an honest label about what was actually done:

| Level | Meaning |
| --- | --- |
| `L0` | reasoning only, no retrieved passage confirmed it |
| `L1` | cross-checked against a verified retrieved passage |
| `L2` | modelled or computed |
| `L3` | executed in a sandbox |

Never render an idea as validated without its level. Never let a "validated" badge appear on an `L0` idea.

## Visual and Motion Principles

- Design an editorial research instrument: strong type hierarchy, quiet surfaces, compact but readable metadata, evidence-forward layouts, and a distinctive visual anchor.
- Use motion with a job. Good examples: reveal how a source is derived as the user scrolls; briefly highlight the active stage; expand a source inspector from its selected row.
- Keep content and controls usable before, during, and without animation. Never make source reading wait for a sequence to finish.
- Prefer low-amplitude opacity/position changes and stable framing over continuous parallax, spinning orbits, or large peripheral motion.
- Support `prefers-reduced-motion`; remove scroll-linked transforms, long transitions, looping pulses, and smooth scrolling while keeping all state distinctions visible.
- Keep typography readable and status cues redundant: do not rely on color or motion alone.

## Product Priorities

1. Make source collection reviewable: deduplicate, filter, inspect, mark reviewed/excluded, and persist review state.
2. Add source-quality and freshness context, including explicit unknown dates and snippet-only extraction.
3. Let analysts create claims from selected passages, attach supporting and opposing evidence, and record open questions.
4. Add model assistance as provisional suggestions with passage citations and analyst approval; do not call simple source links verification.
5. Add monitoring, change detection, collaboration, and exports after repeat use validates those needs.

## External Design References

Use current platform and accessibility guidance, not visual imitation:

- Apple Human Interface Guidelines, Motion: https://developer.apple.com/design/human-interface-guidelines/motion
- Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines/
- WCAG 2.2, Animation from Interactions (2.3.3): https://www.w3.org/TR/WCAG22/#animation-from-interactions

Apple's motion guidance recommends purposeful, optional, brief feedback that maintains continuity and avoids distracting movement. Apply the principle to web scrollytelling; do not reproduce Apple page assets or proprietary visual designs.
