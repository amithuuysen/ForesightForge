"""Autonomous R&D workflow for ForesightForge.

The pipeline replaces a business analyst, research analyst and R&D department for a
given technology domain. It runs a council of specialists that:

1. plan the investigation and decompose it into parallel subagent tasks
2. deconstruct the target system into first-principles primitives and isolate the
   root-cause bottleneck
3. gather real prior art and evidence from the public web
4. adversarially stress-test the diagnosis
5. cross-examine the council, recording disagreements
6. iterate on contested points until the council converges
7. cross-pollinate paradigms from adjacent fields into new inventions
8. model the quantitative trajectory and forecast
9. verify citations at passage level and score the work with a rigour rubric

Every stage emits progress events so the client can render the deliberation live.
The workflow degrades honestly: without a model provider it still collects and
cites real evidence, but it never fabricates architectural claims.
"""

from __future__ import annotations

import json
from typing import Any, Callable, TypedDict, cast
from uuid import uuid4

from .config import settings
from .llm import call_llm, call_llm_json, resolve_provider
from .roles import COUNCIL_PERSONAS, estimate_cost_usd, resolve_model
from .sources import SearchProviderError, search_web


STAGES = (
    "plan",
    "deconstruct",
    "gather",
    "attack",
    "cross_examine",
    "refine_attempt",
    "cross-pollinate",
    "project",
    "synthesize",
    "cite",
    "verify",
    "validate",
)

ProgressCallback = Callable[[dict[str, object]], None]

COUNCIL = tuple((persona.id, persona.name, persona.mandate) for persona in COUNCIL_PERSONAS)


class ResearchState(TypedDict, total=False):
    run_id: str
    domain: str
    question: str
    mode: str
    limits: dict[str, object]
    spend: dict[str, object]
    current_stage: str
    round: int
    attempt: int
    max_attempts: int
    tool_calls: int
    audit: list[dict[str, str]]
    status: str
    intake: dict[str, object]
    clarifying_questions: list[dict[str, object]]
    scope: dict[str, object]
    pain_points: list[dict[str, object]]
    transcript: list[dict[str, object]]
    panel_round: int
    convergence: float
    problem_candidates: list[dict[str, object]]
    selected_problem_ids: list[str]
    claims: list[dict[str, object]]
    sources: list[dict[str, object]]
    evidence: list[dict[str, object]]
    gaps: list[dict[str, object]]
    ideas: list[dict[str, object]]
    critiques: list[dict[str, object]]
    lineage: list[dict[str, object]]
    validation_results: list[dict[str, object]]
    ranked_ideas: list[dict[str, object]]
    checkpoints: list[dict[str, object]]
    pending_checkpoint: dict[str, object] | None
    plan: dict[str, object]
    subagent_executions: list[dict[str, object]]
    citation_verifications: list[dict[str, object]]
    evaluation: dict[str, object]
    forecast: dict[str, object]
    disagreements: list[dict[str, object]]
    projections: list[dict[str, object]]
    brainstormed_ideas: list[dict[str, object]]
    overcome_strategies: list[dict[str, object]]
    active_speaker: dict[str, object]
    core_architecture: dict[str, object]
    attempt_history: list[dict[str, object]]
    provider_failures: list[str]
    progress_callback: ProgressCallback
    model_provider: str | None
    model_name: str | None
    api_key: str | None


def _emit(state: ResearchState, event: dict[str, object]) -> None:
    """Publish a progress event and record it in the run audit trail."""
    callback = state.get("progress_callback")
    if callback:
        callback(event)
    stage = str(event.get("stage", state.get("current_stage", "workflow")))
    detail = str(event.get("detail", event.get("title", "")))
    event_name = str(event.get("type", "progress"))
    state.setdefault("audit", []).append(
        {"stage": stage, "event": event_name, "detail": detail}
    )


def _speak(state: ResearchState, speaker_id: str, speech: str, stage: str) -> None:
    """Mark a council member as the current speaker and announce their turn."""
    name = next((title for key, title, _ in COUNCIL if key == speaker_id), speaker_id)
    role = next((role for key, _, role in COUNCIL if key == speaker_id), "")
    state["active_speaker"] = {
        "id": speaker_id,
        "name": name,
        "role": role,
        "speech": speech,
        "stage": stage,
    }
    _emit(
        state,
        {
            "type": "agent_speech",
            "stage": stage,
            "speaker_id": speaker_id,
            "speaker_name": name,
            "speech": speech,
            "detail": f"{name}: {speech}",
        },
    )


def _context(sources: list[dict[str, object]], limit: int | None = None) -> str:
    """Render retrieved source text into a bounded context block for the model."""
    limit = limit or settings.workflow.context_chars
    blocks: list[str] = []
    used = 0
    for source in sources:
        text = str(source.get("content") or source.get("excerpt") or "").strip()
        if not text:
            continue
        header = f"[{source.get('title', 'Untitled')} | {source.get('publisher') or 'unknown publisher'}]"
        block = f"{header}\n{text}"
        if used + len(block) > limit:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks) if blocks else "(no retrieved source text available)"


def _llm(
    state: ResearchState,
    prompt: str,
    system_prompt: str | None = None,
) -> dict[str, Any] | None:
    """Call the configured model provider with workflow defaults.

    This is the path the original council stages use. It charges the run
    budget exactly like the role-based path, so the spend meter reflects every
    model call the run makes.
    """
    state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
    if state["tool_calls"] > settings.workflow.max_tool_calls:
        return None
    if _budget_exhausted(state):
        return None
    provider = state.get("model_provider")
    payload = call_llm_json(
        prompt,
        system_prompt=system_prompt,
        provider=provider,
        model=state.get("model_name"),
        api_key=state.get("api_key"),
        temperature=settings.workflow.llm_temperature,
    )
    if payload is None:
        _mark_provider_failure(state, "council")
        return None
    _charge_spend(state, provider, prompt, json.dumps(payload))
    return payload


def call_role_llm_json(
    state: dict[str, Any],
    agent: str,
    prompt: str,
    system_prompt: str | None = None,
) -> dict[str, Any] | None:
    """Call the model configured for an agent role and record its spend.

    The role resolves to a tier in ``config/models.yaml`` which resolves to a
    provider and model. A tier may pin a different vendor, which is how the
    skeptic ends up on a model that did not write the idea it is attacking.
    Spend is estimated from token counts and charged against the run budget.
    """
    spec = resolve_model(agent)
    state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
    if state["tool_calls"] > settings.workflow.max_tool_calls:
        return None
    if _budget_exhausted(state):
        return None

    model = spec["model"]
    provider = state.get("model_provider")
    if model and ":" in model:
        pinned_provider, pinned_model = model.split(":", 1)
        provider = pinned_provider.strip() or provider
        model = pinned_model.strip()
    if not model:
        model = state.get("model_name")

    payload = call_llm_json(
        prompt,
        system_prompt=system_prompt,
        provider=provider,
        model=model,
        api_key=state.get("api_key"),
        temperature=spec["temperature"],
    )
    if payload is None:
        # A failed call costs the provider nothing, so it must not be charged.
        _mark_provider_failure(state, agent)
        return None
    _charge_spend(state, provider, prompt, json.dumps(payload))
    return payload


def _mark_provider_failure(state: dict[str, Any], agent: str) -> None:
    """Record that a role could not reach its model, once per role."""
    failures = state.setdefault("provider_failures", [])
    if agent in failures:
        return
    failures.append(agent)
    _emit(
        state,
        {
            "type": "provider_unavailable",
            "stage": str(state.get("current_stage", "workflow")),
            "title": f"{agent} could not reach a model provider",
            "detail": (
                "This role ran without model reasoning. Evidence retrieval and citation "
                "verification still work; analysis does not."
            ),
            "agent": agent,
        },
    )


def _charge_spend(
    state: dict[str, Any],
    provider: str | None,
    prompt: str,
    completion: str,
) -> None:
    """Estimate and accumulate the cost of one model call."""
    usd, tokens = estimate_cost_usd(provider, len(prompt), len(completion))
    spend = dict(state.get("spend") or {})
    spend["usd"] = round(float(spend.get("usd", 0.0)) + usd, 6)
    spend["tokens"] = int(spend.get("tokens", 0)) + tokens
    spend["calls"] = int(spend.get("calls", 0)) + 1
    spend["tool_calls"] = int(state.get("tool_calls", 0))
    state["spend"] = spend
    _emit(
        state,
        {
            "type": "spend_updated",
            "stage": str(state.get("current_stage", "workflow")),
            "detail": f"${spend['usd']:.4f} of ${float((state.get('limits') or {}).get('max_usd', settings.budget.default_max_usd)):.2f} budget",
            "spend": spend,
        },
    )


def _budget_exhausted(state: dict[str, Any]) -> bool:
    """True when the run has spent its user-set budget."""
    limits = state.get("limits") or {}
    max_usd = float(limits.get("max_usd", settings.budget.default_max_usd))
    spend = state.get("spend") or {}
    return float(spend.get("usd", 0.0)) >= max_usd


def _budget_remaining(state: dict[str, Any]) -> float:
    limits = state.get("limits") or {}
    max_usd = float(limits.get("max_usd", settings.budget.default_max_usd))
    spend = state.get("spend") or {}
    return max(0.0, round(max_usd - float(spend.get("usd", 0.0)), 4))


def _model_available(state: ResearchState) -> bool:
    provider, _key, _config = resolve_provider(
        state.get("model_provider"),
        state.get("api_key"),
    )
    return provider is not None


def classify_intake(state: ResearchState) -> ResearchState:
    """Classify the user's input as a problem, a topic, or ambiguous (FR-IN-1).

    A problem describes something that is failing or blocking. A topic names a
    field or subject to explore. When the signal is weak the system asks at most
    two clarifying questions and states the assumption it will proceed on.
    """
    state["current_stage"] = "intake"
    raw_input = state.get("question", "")
    domain = state.get("domain", "")

    _emit(
        state,
        {
            "type": "intake_started",
            "stage": "intake",
            "detail": "Classifying the input as a problem, a topic, or ambiguous",
        },
    )

    payload = call_role_llm_json(
        state,
        "classify_intake",
        f"""Classify this research request.

DOMAIN HINT: {domain}
USER INPUT: {raw_input}

A "problem" describes something failing, blocked, limiting or expensive right now.
A "topic" names a field, subject or area the user wants to explore.
An "ambiguous" input could reasonably be read as either.

Respond with JSON:
{{
  "mode": "problem" | "topic" | "ambiguous",
  "confidence": 0.0 to 1.0,
  "reasoning": "one sentence on how you read the input",
  "problem_statement": "if problem, the problem restated as a concrete engineering or research problem",
  "clarifying_questions": ["at most 2 questions, only if mode is ambiguous"]
}}""",
    )

    mode = str((payload or {}).get("mode") or "problem").lower()
    if mode not in {"problem", "topic", "ambiguous"}:
        mode = "problem"

    intake: dict[str, object] = {
        "mode": mode,
        "confidence": float((payload or {}).get("confidence") or 0.0),
        "reasoning": str((payload or {}).get("reasoning") or ""),
        "classified_by": "model" if payload else "heuristic",
    }
    questions: list[dict[str, object]] = []

    if mode == "problem":
        intake["problem_statement"] = str((payload or {}).get("problem_statement") or raw_input)
    elif mode == "topic":
        intake["topic"] = str((payload or {}).get("topic") or domain or raw_input)
    else:
        raw_questions = (payload or {}).get("clarifying_questions") or []
        questions = [
            {"id": f"q{index + 1}", "question": str(item)[:300], "answer": ""}
            for index, item in enumerate(raw_questions[:2])
        ]
        if not questions:
            questions = [
                {
                    "id": "q1",
                    "question": "Are you blocked by a specific failure, or exploring the field?",
                    "answer": "",
                }
            ]
        intake["assumed_mode"] = "topic"
        intake["assumption"] = (
            "Proceeding in Topic Discovery mode because the input names an area rather than a failure."
        )

    state["intake"] = intake
    state["mode"] = intake["mode"]
    state["clarifying_questions"] = questions

    if questions:
        _emit(
            state,
            {
                "type": "clarifying_requested",
                "stage": "intake",
                "title": "Two clarifying questions before the council convenes",
                "detail": " · ".join(str(item["question"]) for item in questions),
                "questions": questions,
            },
        )
    else:
        _emit(
            state,
            {
                "type": "intake_classified",
                "stage": "intake",
                "title": f"Input classified as {mode}",
                "detail": str(intake.get("reasoning") or intake.get("assumption") or ""),
                "mode": mode,
            },
        )
    return state


def _stage_plan(state: ResearchState) -> ResearchState:
    """Principal Investigator frames the investigation and decomposes it."""
    state["current_stage"] = "plan"
    domain = state.get("domain", "")
    question = state.get("question", "")
    _speak(
        state,
        "lead",
        f"Framing the investigation into {domain}: {question}",
        "plan",
    )

    plan = _llm(
        state,
        f"""You are the Principal Investigator of an autonomous R&D council.
Formulate a customized research plan to solve this problem.

DOMAIN: {domain}
QUESTION: {question}

Respond with JSON:
{{
  "complexity": "simple_fact_finding" | "comparative_analysis" | "multi_faceted_research",
  "rationale": "why this plan",
  "subagent_count": {settings.workflow.max_subagents},
  "tool_budget_per_agent": 4,
  "convening_speech": "opening statement to the council",
  "objectives": ["..."],
  "subtasks": [
    {{
      "subagent_id": "subagent-1",
      "role": "Role title",
      "focus": "What this fellow investigates",
      "boundaries": "What this fellow must not claim",
      "search_strategy": "start_broad_then_narrow",
      "broad_query": "search string",
      "narrow_query_templates": ["..."]
    }}
  ]
}}

Hard limits: at most {settings.workflow.max_subagents} subtasks, at most 5 objectives,
and every text field under 200 characters. A response that exceeds the token budget
is discarded, so brevity is required.""",
        system_prompt="You plan rigorous, first-principles R&D investigations. Respond only in JSON.",
    )

    if plan:
        state["plan"] = plan
        _speak(
            state,
            "lead",
            str(plan.get("convening_speech") or plan.get("rationale") or "Council convened."),
            "plan",
        )
        _emit(
            state,
            {
                "type": "plan_created",
                "stage": "plan",
                "complexity": plan.get("complexity"),
                "subagent_count": plan.get("subagent_count"),
                "rationale": plan.get("rationale"),
                "objectives": plan.get("objectives"),
                "subtasks": plan.get("subtasks"),
                "detail": f"Investigation decomposed into {len(plan.get('subtasks') or [])} parallel subagent tasks.",
            },
        )
    else:
        _emit(
            state,
            {
                "type": "plan_created",
                "stage": "plan",
                "detail": "No model provider configured; running with a single-pass evidence collection plan.",
            },
        )
    return state


def _stage_deconstruct(state: ResearchState) -> ResearchState:
    """Architecture Fellow deconstructs the system into first principles."""
    state["current_stage"] = "deconstruct"
    domain = state.get("domain", "")
    question = state.get("question", "")
    _speak(state, "subagent-1", f"Deconstructing the base architecture of {domain}.", "deconstruct")

    architecture = _llm(
        state,
        f"""Deconstruct the first-principles base core architecture of this technology system.

DOMAIN: {domain}
QUESTION: {question}

Respond with JSON:
{{
  "system_name": "Formal name of the system/architecture",
  "domain": "{domain}",
  "foundational_summary": "2-3 sentences on how the system works",
  "governing_equation": "The governing mathematical or physical relation (LaTeX or plain text)",
  "primitives": [
    {{
      "name": "Primitive name",
      "category": "Component class",
      "mechanism": "How it physically/technologically works",
      "role_in_system": "What it contributes to the whole",
      "bottleneck_equation_or_limit": "The physical or computational limit it imposes"
    }}
  ],
  "flaw_hotspot": "The single isolated root-cause bottleneck",
  "diagnostic_speech": "One sentence on the diagnosis"
}}

Hard limits: at most 5 primitives, and every text field under 250 characters.
A response that exceeds the token budget is discarded, so brevity is required.""",
        system_prompt="You are a principal investigator in deep technology. You reason from first principles.",
    )

    if architecture:
        state["core_architecture"] = architecture
        _speak(
            state,
            "subagent-1",
            str(
                architecture.get("diagnostic_speech")
                or f"Isolated root cause: {architecture.get('flaw_hotspot', 'unknown')}"
            ),
            "deconstruct",
        )
        _emit(
            state,
            {
                "type": "architecture_deconstructed",
                "stage": "deconstruct",
                "title": architecture.get("system_name"),
                "detail": str(architecture.get("foundational_summary", "")),
            },
        )
    else:
        _emit(
            state,
            {
                "type": "architecture_deconstructed",
                "stage": "deconstruct",
                "detail": "No model provider configured; architecture deconstruction requires a model and was skipped.",
            },
        )
    return state


def _stage_gather(state: ResearchState) -> ResearchState:
    """Research subagents collect real prior art and evidence from the public web."""
    state["current_stage"] = "gather"
    plan = state.get("plan") or {}
    raw_subtasks = plan.get("subtasks")
    subtasks: list[dict[str, Any]] = [
        dict(task) for task in raw_subtasks if isinstance(task, dict)
    ] if isinstance(raw_subtasks, list) else []
    domain = state.get("domain", "")
    question = state.get("question", "")

    if not subtasks:
        subtasks = [
            {
                "subagent_id": "subagent-1",
                "role": "Evidence Research Fellow",
                "focus": question,
                "boundaries": "Report only what retrieved sources state.",
                "broad_query": f"{domain} {question}",
                "narrow_query_templates": [],
            }
        ]

    executions: list[dict[str, object]] = []
    all_sources: list[dict[str, object]] = []
    seen_urls: set[str] = set()

    for subtask in subtasks[: settings.workflow.max_subagents]:
        subagent_id = str(subtask.get("subagent_id") or "subagent-1")
        role = str(subtask.get("role") or "Research Fellow")
        focus = str(subtask.get("focus") or question)
        boundaries = str(subtask.get("boundaries") or "Cite only retrieved sources.")
        broad_query = str(subtask.get("broad_query") or f"{domain} {focus}")
        narrow = list(subtask.get("narrow_query_templates") or [])

        _speak(
            state,
            subagent_id,
            f"Investigating {focus} within boundaries: {boundaries}",
            "gather",
        )
        _emit(
            state,
            {
                "type": "subagent_started",
                "stage": "gather",
                "subagent_id": subagent_id,
                "role": role,
                "focus": focus,
                "boundaries": boundaries,
                "detail": f"{role} began investigating: {focus}",
            },
        )

        queries = [broad_query, *[str(item) for item in narrow[:1]]]
        executed: list[str] = []
        subtask_sources: list[dict[str, object]] = []

        for query in queries:
            if not query.strip():
                continue
            executed.append(query)
            try:
                found = search_web(
                    domain,
                    query,
                    progress_callback=lambda event, _sid=subagent_id: _emit(
                        state, {**event, "stage": "gather", "subagent_id": _sid}
                    ),
                )
            except SearchProviderError as error:
                _emit(
                    state,
                    {
                        "type": "source_search_failed",
                        "stage": "gather",
                        "subagent_id": subagent_id,
                        "detail": str(error),
                    },
                )
                continue
            for source in found:
                url = str(source.get("url", ""))
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                subtask_sources.append(source)
                all_sources.append(source)
                if len(all_sources) >= settings.search.max_sources:
                    break
            if len(all_sources) >= settings.search.max_sources:
                break

        thinking: list[dict[str, object]] = []
        findings: list[str] = []

        if subtask_sources and _model_available(state):
            context = _context(subtask_sources)
            analysis = _llm(
                state,
                f"""You are {role}. Focus: {focus}. Boundaries: {boundaries}.
Extract findings strictly from the retrieved evidence below.

RETRIEVED EVIDENCE:
{context}

Respond with JSON:
{{
  "thinking_trace": [
    {{"step_index": 1, "action": "what you did", "scratchpad": "reasoning", "decision": "decision"}}
  ],
  "key_findings": ["finding 1", "finding 2"]
}}""",
                system_prompt="You are a rigorous research fellow. Never state anything the evidence does not support.",
            )
            if analysis:
                thinking = list(analysis.get("thinking_trace") or [])
                findings = list(analysis.get("key_findings") or [])

        for step in thinking:
            _emit(
                state,
                {
                    "type": "thinking_step",
                    "stage": "gather",
                    "subagent_id": subagent_id,
                    "action": step.get("action"),
                    "scratchpad": step.get("scratchpad"),
                    "decision": step.get("decision"),
                    "detail": str(step.get("scratchpad") or step.get("decision") or ""),
                },
            )

        executions.append(
            {
                "subagent_id": subagent_id,
                "role": role,
                "status": "completed",
                "queries_executed": executed,
                "sources_found": len(subtask_sources),
                "thinking_trace": thinking,
                "key_findings": findings,
            }
        )
        _emit(
            state,
            {
                "type": "subagent_completed",
                "stage": "gather",
                "subagent_id": subagent_id,
                "role": role,
                "detail": f"{role} gathered {len(subtask_sources)} source(s) across {len(executed)} query path(s).",
            },
        )

    state["subagent_executions"] = executions
    state["sources"] = all_sources
    _emit(
        state,
        {
            "type": "sources_found",
            "stage": "gather",
            "source_count": len(all_sources),
            "detail": f"Retrieved {len(all_sources)} source(s) from public web search.",
        },
    )
    return state


def _stage_attack(state: ResearchState) -> ResearchState:
    """Adversarial Red-Team stress-tests the diagnosis."""
    state["current_stage"] = "attack"
    domain = state.get("domain", "")
    architecture = state.get("core_architecture") or {}
    flaw = str(architecture.get("flaw_hotspot") or "the proposed architecture")
    _speak(state, "subagent-3", f"Stress-testing the diagnosis: {flaw}", "attack")

    stress = _llm(
        state,
        f"""Adversarial stress-test attack on this engineering diagnosis.

DOMAIN: {domain}
DIAGNOSED FLAW: {flaw}
PRIMITIVES: {architecture.get("primitives")}

Respond with JSON:
{{
  "speech": "Your adversarial assessment",
  "critical_vulnerability": "The most likely way this solution fails"
}}""",
        system_prompt="You are a red-team engineer. Be specific and sceptical.",
    )

    if stress:
        _speak(state, "subagent-3", str(stress.get("speech", "")), "attack")
        _emit(
            state,
            {
                "type": "adversarial_stress_test",
                "stage": "attack",
                "speech": stress.get("speech"),
                "detail": str(stress.get("critical_vulnerability", "")),
            },
        )
    else:
        _emit(
            state,
            {
                "type": "adversarial_stress_test",
                "stage": "attack",
                "detail": "Adversarial review requires a model provider and was skipped.",
            },
        )
    return state


def _stage_cross_examine(state: ResearchState) -> ResearchState:
    """The council cross-examines the diagnosis and records disagreements."""
    state["current_stage"] = "cross_examine"
    domain = state.get("domain", "")
    question = state.get("question", "")
    architecture = state.get("core_architecture") or {}
    context = _context(state.get("sources") or [])

    examination = _llm(
        state,
        f"""Conduct a council cross-examination of this R&D diagnosis.

DOMAIN: {domain}
QUESTION: {question}
DIAGNOSED FLAW: {architecture.get("flaw_hotspot")}
EVIDENCE:
{context}

Respond with JSON:
{{
  "turns": [
    {{"speaker_id": "subagent-3", "speaker_name": "Adversarial Red-Team", "speech": "..."}},
    {{"speaker_id": "subagent-2", "speaker_name": "Cross-Domain Invention Fellow", "speech": "..."}},
    {{"speaker_id": "lead", "speaker_name": "Principal Investigator", "speech": "..."}}
  ],
  "disagreements": [
    {{
      "id": "disagree-1",
      "speaker_a": "...",
      "role_a": "...",
      "stance_a": "...",
      "speaker_b": "...",
      "role_b": "...",
      "stance_b": "..."
    }}
  ]
}}""",
        system_prompt="You facilitate a rigorous scientific council. Each speaker holds a distinct position.",
    )

    if examination:
        for turn in examination.get("turns") or []:
            _speak(
                state,
                str(turn.get("speaker_id") or "lead"),
                str(turn.get("speech") or ""),
                "cross_examine",
            )
        disagreements = list(examination.get("disagreements") or [])
        state["disagreements"] = disagreements
        for disagreement in disagreements:
            _emit(
                state,
                {
                    "type": "disagreement",
                    "stage": "cross_examine",
                    "detail": (
                        f"{disagreement.get('speaker_a', 'Agent A')} vs "
                        f"{disagreement.get('speaker_b', 'Agent B')}: "
                        f"{disagreement.get('stance_a', '')}"
                    ),
                },
            )
    else:
        _emit(
            state,
            {
                "type": "cross_examination",
                "stage": "cross_examine",
                "detail": "Council cross-examination requires a model provider and was skipped.",
            },
        )
    return state


def _stage_refine_attempt(state: ResearchState) -> ResearchState:
    """Resolve contested points and record the attempt convergence."""
    state["current_stage"] = "refine_attempt"
    # Attempt 1 is the initial council pass; refinement opens attempt 2.
    attempt = int(state.get("attempt", 1)) + 1
    max_attempts = settings.workflow.max_attempts
    state["attempt"] = attempt
    state["max_attempts"] = max_attempts
    disagreements = state.get("disagreements") or []

    _speak(
        state,
        "lead",
        f"Attempt {attempt}: resolving {len(disagreements)} contested point(s).",
        "refine_attempt",
    )

    refinement = _llm(
        state,
        f"""Resolve the contested points from this council review.

DOMAIN: {state.get("domain", "")}
DISAGREEMENTS: {disagreements}
CONTEXT: {_context(state.get("sources") or [])}

Attempt {attempt} to resolve contested points and reach convergence.

Respond with JSON:
{{
  "attempt_focus": "What this attempt re-investigated",
  "convergence_score": 0.0,
  "pi_speech": "Principal Investigator resolution",
  "red_team_speech": "Red-Team concession or remaining objection"
}}""",
        system_prompt="You are the Principal Investigator closing out contested points with evidence.",
    )

    convergence = 0.0
    focus = ""
    if refinement:
        convergence = float(refinement.get("convergence_score") or 0.0)
        focus = str(refinement.get("attempt_focus") or "")
        _speak(state, "lead", str(refinement.get("pi_speech") or focus), "refine_attempt")
        if refinement.get("red_team_speech"):
            _speak(state, "subagent-3", str(refinement["red_team_speech"]), "refine_attempt")
    else:
        focus = "Evidence collection only; no model available to converge the council."
        convergence = 0.0

    history = list(state.get("attempt_history") or [])
    history.append(
        {
            "attempt": attempt,
            "max_attempts": max_attempts,
            "status": "converged" if convergence >= settings.workflow.convergence_threshold else "open",
            "convergence_score": convergence,
            "focus": focus,
        }
    )
    state["attempt_history"] = history

    _emit(
        state,
        {
            "type": "attempt_2_to_resolve_contested_points",
            "stage": "refine_attempt",
            "attempt": attempt,
            "attempt_focus": focus,
            "convergence_score": convergence,
            "detail": f"Attempt {attempt} convergence {convergence:.2f}: {focus}",
        },
    )

    if convergence < settings.workflow.convergence_threshold and attempt < max_attempts:
        state["attempt"] = attempt
    return state


def _stage_cross_pollinate(state: ResearchState) -> ResearchState:
    """Transfer paradigms from adjacent fields into new inventions."""
    state["current_stage"] = "cross-pollinate"
    domain = state.get("domain", "")
    architecture = state.get("core_architecture") or {}
    flaw = str(architecture.get("flaw_hotspot") or "the diagnosed bottleneck")
    _speak(
        state,
        "subagent-2",
        f"Transferring paradigms from adjacent fields to defeat: {flaw}",
        "cross-pollinate",
    )

    invention = _llm(
        state,
        f"""Propose breakthrough inventions that solve this bottleneck by transferring
mechanisms from adjacent scientific and engineering domains.

DOMAIN: {domain}
BOTTLENECK: {flaw}
PRIMITIVES: {architecture.get("primitives")}
EVIDENCE: {_context(state.get("sources") or [])}

Respond with JSON:
{{
  "brainstormed_ideas": [
    {{
      "id": "idea-1",
      "title": "Invention title",
      "transferred_domain": "The adjacent field the mechanism came from",
      "mechanism": "How the transferred mechanism works here",
      "flaw_addressed": "Which diagnosed flaw this removes",
      "feasibility_score": 0,
      "experiment_protocol": "Laboratory validation protocol",
      "expected_impact": "Expected measurable gain"
    }}
  ],
  "overcome_strategies": [
    {{
      "bottleneck": "Diagnosed bottleneck",
      "solution_strategy": "How it is removed",
      "primary_mechanism": "The core physical/technical mechanism",
      "expected_gain": "Expected measurable improvement"
    }}
  ]
}}

Hard limits: at most 3 ideas and 3 strategies. Every text field must be under
200 characters. A response that exceeds the token budget is discarded, so
being concise is required, not optional.""",
        system_prompt="You invent by analogy across disciplines. Be concrete and physically plausible.",
    )

    ideas = list((invention or {}).get("brainstormed_ideas") or [])
    strategies = list((invention or {}).get("overcome_strategies") or [])
    state["brainstormed_ideas"] = ideas
    state["overcome_strategies"] = strategies

    # Promote the inventions into the PRD idea model so they can be validated,
    # challenged and ranked like any other idea.
    promoted: list[dict[str, object]] = []
    strategy_by_bottleneck = {
        str(item.get("bottleneck", "")): item for item in strategies if isinstance(item, dict)
    }
    for index, idea in enumerate(ideas):
        bottleneck = str(idea.get("flaw_addressed") or "")
        strategy = strategy_by_bottleneck.get(bottleneck, {})
        promoted.append(
            {
                "id": str(idea.get("id") or f"idea-{index + 1}"),
                "title": str(idea.get("title") or "Untitled invention")[:300],
                "operator": "transfer",
                "description": str(idea.get("mechanism") or "")[:1400],
                "why_it_should_work": str(strategy.get("primary_mechanism") or idea.get("mechanism") or "")[:900],
                "targets": bottleneck,
                "transferred_domain": str(idea.get("transferred_domain") or "")[:200],
                "evidence_ids": [],
                "status": "proposed",
                "critiques": [],
                "validation_level": "L0",
                "next_test": str(idea.get("experiment_protocol") or "")[:600],
                "cheapest_test": str(idea.get("experiment_protocol") or "")[:600],
                "risks": [],
                "kill_reason": None,
                "expected_impact": str(idea.get("expected_impact") or "")[:600],
                "feasibility_score": float(idea.get("feasibility_score") or 0.0),
            }
        )
    state["ideas"] = promoted

    for idea in ideas:
        _emit(
            state,
            {
                "type": "idea_proposed",
                "stage": "cross-pollinate",
                "idea": idea,
                "detail": f"{idea.get('title', 'Invention')}: {idea.get('mechanism', '')}",
            },
        )
    if not ideas:
        _emit(
            state,
            {
                "type": "cross_pollination",
                "stage": "cross-pollinate",
                "detail": "Invention ideation requires a model provider and was skipped.",
            },
        )
    return state


def _stage_project(state: ResearchState) -> ResearchState:
    """Model the quantitative trajectory of the breakthrough."""
    state["current_stage"] = "project"
    domain = state.get("domain", "")
    ideas = state.get("brainstormed_ideas") or []
    _speak(state, "lead", f"Modelling the scaling trajectory for {domain}.", "project")

    trajectory = _llm(
        state,
        f"""Model the quantitative trajectory of this breakthrough.

DOMAIN: {domain}
INVENTIONS: {ideas}
EVIDENCE: {_context(state.get("sources") or [])}

Produce the quantitative trajectory of the breakthrough over time.

Respond with JSON:
{{
  "metric_name": "The primary performance metric tracked",
  "projections": [
    {{"year": 2026, "target_metric": 0, "baseline_metric": 0, "alt_metric": 0}}
  ]
}}""",
        system_prompt="You model engineering roadmaps quantitatively. Ground every number.",
    )

    projections: list[dict[str, object]] = []
    if trajectory:
        for point in trajectory.get("projections") or []:
            projections.append(
                {
                    "year": int(point.get("year", 0)),
                    "renewables": float(point.get("target_metric", 0)),
                    "fossil": float(point.get("baseline_metric", 0)),
                    "nuclear": float(point.get("alt_metric", 0)),
                }
            )
        state["projections"] = projections
        _emit(
            state,
            {
                "type": "quantitative_trajectory",
                "stage": "project",
                "metric_name": trajectory.get("metric_name"),
                "projections": projections,
                "detail": f"Trajectory modelled across {len(projections)} milestone(s).",
            },
        )
    else:
        _emit(
            state,
            {
                "type": "quantitative_trajectory",
                "stage": "project",
                "detail": "Trajectory modelling requires a model provider and was skipped.",
            },
        )
    return state


def _stage_synthesize(state: ResearchState) -> ResearchState:
    """Synthesize the engineering solution blueprint and forecast."""
    state["current_stage"] = "synthesize"
    domain = state.get("domain", "")
    question = state.get("question", "")
    architecture = state.get("core_architecture") or {}
    ideas = state.get("brainstormed_ideas") or []
    strategies = state.get("overcome_strategies") or []

    _speak(
        state,
        "lead",
        f"Synthesizing the engineering solution blueprint for {domain}.",
        "synthesize",
    )

    synthesis = _llm(
        state,
        f"""Synthesize the final engineering solution and forecast for the end user.

DOMAIN: {domain}
QUESTION: {question}
DIAGNOSED FLAW: {architecture.get("flaw_hotspot")}
INVENTIONS: {ideas}
SOLUTION STRATEGIES: {strategies}

Respond with JSON:
{{
  "verdict": "FEASIBLE | FEASIBLE WITH CONDITIONS | PROVISIONAL | NOT FEASIBLE",
  "headline": "The architectural solution headline, as an architect would state it",
  "confidence_score": 0,
  "confidence_label": "Label for the score, under 4 words",
  "confidence_summary": "Why this confidence",
  "key_drivers": ["The engineered solutions that remove the bottleneck"],
  "key_risks": ["The diagnosed flaws and physical limits that remain"],
  "master_quote": "One closing statement from the lead researcher"
}}

The verdict is a short uppercase label of at most three words, not a sentence.
The reasoning belongs in confidence_summary. A response that exceeds the token
budget is discarded, so brevity is required.""",
        system_prompt="You are the lead researcher delivering a defensible engineering answer.",
    )

    if synthesis:
        forecast = dict(synthesis)
        forecast.setdefault("verdict", "Provisional")
        forecast["brainstormed_ideas"] = ideas
        forecast["overcome_strategies"] = strategies
        forecast["core_architecture"] = architecture
        state["forecast"] = forecast
        state["core_architecture"] = architecture
        _speak(
            state,
            "lead",
            str(synthesis.get("master_quote") or synthesis.get("headline", "")),
            "synthesize",
        )
        _emit(
            state,
            {
                "type": "solution_synthesized",
                "stage": "synthesize",
                "forecast": forecast,
                "detail": str(synthesis.get("headline", "")),
            },
        )
    else:
        _emit(
            state,
            {
                "type": "solution_synthesized",
                "stage": "synthesize",
                "detail": "Solution synthesis requires a model provider and was skipped.",
            },
        )
    return state


def _stage_cite(state: ResearchState) -> ResearchState:
    """Verify citations at passage level against the retrieved sources."""
    state["current_stage"] = "cite"
    sources = state.get("sources") or []
    claims = state.get("claims") or []
    _speak(
        state,
        "citation",
        f"Verifying {len(claims)} claim(s) against {len(sources)} retrieved source(s).",
        "cite",
    )

    verifications: list[dict[str, object]] = []
    if claims and sources and _model_available(state):
        for claim in claims:
            claim_id = str(claim.get("id", ""))
            claim_text = str(claim.get("text", ""))
            passages = _llm(
                state,
                f"""Find the exact supporting passage in the evidence for this claim.

CLAIM: {claim_text}
EVIDENCE:
{_context(sources)}

Respond with JSON:
{{
  "source_id": "id of the supporting source",
  "source_title": "title",
  "source_url": "url",
  "exact_passage": "The verbatim sentence(s) that support the claim",
  "attribution_type": "direct" | "inferred" | "contradicted",
  "match_confidence": 0
}}""",
                system_prompt="You are a citation auditor. Quote the evidence verbatim or report no match.",
            )
            if passages:
                verifications.append(
                    {
                        "claim_id": claim_id,
                        "source_id": passages.get("source_id"),
                        "source_title": passages.get("source_title"),
                        "source_url": passages.get("source_url"),
                        "exact_passage": passages.get("exact_passage"),
                        "attribution_type": passages.get("attribution_type"),
                        "match_confidence": passages.get("match_confidence"),
                    }
                )
                _emit(
                    state,
                    {
                        "type": "citation_verified",
                        "stage": "cite",
                        "claim_id": claim_id,
                        "source_id": passages.get("source_id"),
                        "passage": passages.get("exact_passage"),
                        "detail": (
                            f"Claim matched to {passages.get('source_title', 'source')} "
                            f"at {passages.get('match_confidence', 0)} confidence."
                        ),
                    },
                )
    state["citation_verifications"] = verifications
    if not verifications:
        _emit(
            state,
            {
                "type": "citation_verification",
                "stage": "cite",
                "detail": "No passage-level citations were produced; claims remain uncited.",
            },
        )
    return state


def _stage_verify(state: ResearchState) -> ResearchState:
    """Judge the work against the rigour rubric and apply the evidence gate."""
    state["current_stage"] = "verify"
    sources = state.get("sources") or []
    claims = state.get("claims") or []
    verifications = state.get("citation_verifications") or []
    architecture = state.get("core_architecture") or {}

    _speak(state, "judge", "Evaluating scientific rigour and evidence sufficiency.", "verify")

    rubric = _llm(
        state,
        f"""Score this R&D investigation with the scientific rigour judge rubric.

DOMAIN: {state.get("domain", "")}
CLAIMS: {claims}
CITATIONS: {verifications}
SOURCES: {len(sources)}

Respond with JSON:
{{
  "factual_accuracy": 0,
  "citation_accuracy": 0,
  "completeness": 0,
  "source_quality": 0,
  "tool_efficiency": 0,
  "overall_score": 0,
  "verdict": "PASS" | "NEEDS_EVIDENCE",
  "evaluator_notes": "Assessment"
}}""",
        system_prompt="You are an independent scientific rigour judge. Be strict and evidence-bound.",
    )

    if rubric:
        state["evaluation"] = rubric
        _speak(
            state,
            "judge",
            str(rubric.get("evaluator_notes") or rubric.get("verdict", "")),
            "verify",
        )
        _emit(
            state,
            {
                "type": "rigour_judged",
                "stage": "verify",
                "evaluation": rubric,
                "detail": (
                    f"Council verdict {rubric.get('verdict', 'unknown')} "
                    f"at {rubric.get('overall_score', 0)}."
                ),
            },
        )
    else:
        _emit(
            state,
            {
                "type": "rigour_judged",
                "stage": "verify",
                "detail": "Rigour judging requires a model provider and was skipped.",
            },
        )

    available_source_ids = {
        str(source.get("id"))
        for source in sources
        if isinstance(source.get("id"), str)
    }
    cited_claim_ids = {
        str(verification.get("claim_id"))
        for verification in verifications
        if verification.get("source_id") in available_source_ids
    }
    has_cited_claim = any(str(claim.get("id")) in cited_claim_ids for claim in claims)

    if settings.require_citation:
        status = "completed" if has_cited_claim else "needs_evidence"
        detail = (
            "Every claim resolved to a retrieved passage."
            if has_cited_claim
            else "Claims without a passage-level citation cannot pass verification."
        )
    else:
        status = "completed" if claims else "needs_evidence"
        detail = "Claims present; citation requirement disabled by configuration."

    state["status"] = status
    if not architecture and claims:
        _emit(
            state,
            {
                "type": "verify",
                "stage": "verify",
                "detail": "No architecture deconstruction was produced for this run.",
            },
        )
    _emit(
        state,
        {
            "type": "gate_passed" if status == "completed" else "gate_blocked",
            "stage": "verify",
            "detail": detail,
        },
    )
    return state


def _stage_validate_and_rank(state: ResearchState) -> ResearchState:
    """Assign validation levels, then rank the surviving ideas (FR-VL-1, FR-RS-9).

    Validation levels are honest about what was actually done:
    ``L0`` reasoning only, ``L1`` cross-checked against retrieved evidence,
    ``L2`` modelled or computed, ``L3`` executed in a sandbox. An idea that
    only ever received a reasoning pass stays at L0 and says so.
    """
    state["current_stage"] = "validate"
    ideas = list(state.get("ideas") or [])
    verifications = state.get("citation_verifications") or []
    sources = state.get("sources") or []

    _speak(state, "judge", "Assigning validation levels and ranking the shortlist.", "validate")

    verified_source_ids = {
        str(item.get("source_id"))
        for item in verifications
        if float(item.get("match_confidence") or 0.0) >= 0.5
    }
    cited_claim_ids = {str(item.get("claim_id")) for item in verifications}

    for idea in ideas:
        idea_evidence = {str(item) for item in (idea.get("evidence_ids") or [])}
        if idea_evidence & verified_source_ids:
            idea["validation_level"] = "L1"
        else:
            idea["validation_level"] = "L0"
        idea.setdefault("cheapest_test", idea.get("next_test") or "")
        idea.setdefault("risks", [])

    state["ideas"] = ideas

    validation_results = [
        {
            "idea_id": idea.get("id"),
            "title": idea.get("title"),
            "validation_level": idea.get("validation_level"),
            "rationale": (
                "Cross-checked against a verified retrieved passage."
                if idea.get("validation_level") == "L1"
                else "Reasoning only; no retrieved passage confirmed this yet."
            ),
            "cheapest_test": idea.get("cheapest_test") or "",
        }
        for idea in ideas
    ]
    state["validation_results"] = validation_results

    ranking = call_role_llm_json(
        state,
        "ranker",
        f"""Rank the surviving ideas for this investigation.

DOMAIN: {state.get("domain", "")}
QUESTION: {state.get("question", "")}

IDEAS:
{ideas}

Respond with JSON:
{{
  "ranked": [
    {{
      "id": "the idea id",
      "feasibility": 0.0 to 1.0,
      "impact": 0.0 to 1.0,
      "novelty": 0.0 to 1.0,
      "cost_to_test": 0.0 to 1.0,
      "why_it_should_work": "the mechanism, stated concretely",
      "risks": ["what could make this fail"],
      "next_test": "the cheapest feasible test"
    }}
  ]
}}

Hard limits: score every idea you are given, but keep at most 3 risks and every
text field under 200 characters. A response that exceeds the token budget is
discarded, so brevity is required.""",
    )

    scores: dict[str, dict[str, object]] = {}
    for entry in (ranking or {}).get("ranked", []) or []:
        if not isinstance(entry, dict):
            continue
        idea_id = str(entry.get("id") or "")
        if not idea_id:
            continue
        scores[idea_id] = {
            "feasibility": max(0.0, min(1.0, float(entry.get("feasibility") or 0.0))),
            "impact": max(0.0, min(1.0, float(entry.get("impact") or 0.0))),
            "novelty": max(0.0, min(1.0, float(entry.get("novelty") or 0.0))),
            "cost_to_test": max(0.0, min(1.0, float(entry.get("cost_to_test") or 0.0))),
            "why_it_should_work": str(entry.get("why_it_should_work") or "")[:900],
            "risks": [str(item)[:300] for item in (entry.get("risks") or [])][:6],
            "next_test": str(entry.get("next_test") or "")[:600],
        }

    ranked_ideas: list[dict[str, object]] = []
    for idea in ideas:
        idea_id = str(idea.get("id"))
        score = scores.get(idea_id, {})
        feasibility = float(score.get("feasibility", idea.get("feasibility") or 0.0))
        impact = float(score.get("impact", idea.get("impact") or 0.0))
        novelty = float(score.get("novelty", idea.get("novelty") or 0.0))
        cost = float(score.get("cost_to_test", idea.get("cost_to_test") or 0.5))
        total = round(feasibility * 0.25 + impact * 0.35 + novelty * 0.3 + (1.0 - cost) * 0.1, 4)

        enriched = {
            **idea,
            "feasibility": feasibility,
            "impact": impact,
            "novelty": novelty,
            "cost_to_test": cost,
            "why_it_should_work": score.get("why_it_should_work") or idea.get("why_it_should_work", ""),
            "risks": score.get("risks") or idea.get("risks", []),
            "next_test": score.get("next_test") or idea.get("next_test", ""),
            "cheapest_test": score.get("next_test") or idea.get("cheapest_test", ""),
            "score": total,
        }
        if total >= 0.6 and idea.get("status") in {"proposed", "challenged", "validated"}:
            enriched["status"] = "shortlisted"
        ranked_ideas.append(enriched)

    ranked_ideas.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    for position, idea in enumerate(ranked_ideas, start=1):
        idea["rank"] = position

    state["ranked_ideas"] = ranked_ideas
    state["ideas"] = ranked_ideas

    _emit(
        state,
        {
            "type": "ideas_ranked",
            "stage": "validate",
            "title": f"{len(ranked_ideas)} ideas ranked",
            "detail": (
                f"Top: {ranked_ideas[0]['title']}" if ranked_ideas else "No ideas survived to ranking."
            ),
            "ranked_ideas": ranked_ideas,
        },
    )

    if settings.require_human_checkpoint:
        state["status"] = "awaiting_input"
        _emit(
            state,
            {
                "type": "checkpoint_requested",
                "stage": "shortlist",
                "kind": "shortlist",
                "title": "Approve, edit or redirect the shortlist",
                "detail": "The council has ranked the ideas. Choose what to carry forward.",
                "ranked_ideas": ranked_ideas,
            },
        )
    return state


STAGE_HANDLERS = {
    "plan": _stage_plan,
    "deconstruct": _stage_deconstruct,
    "gather": _stage_gather,
    "attack": _stage_attack,
    "cross_examine": _stage_cross_examine,
    "refine_attempt": _stage_refine_attempt,
    "cross-pollinate": _stage_cross_pollinate,
    "project": _stage_project,
    "synthesize": _stage_synthesize,
    "cite": _stage_cite,
    "verify": _stage_verify,
    "validate": _stage_validate_and_rank,
}


def _run_pipeline(state: ResearchState) -> ResearchState:
    """Execute every R&D stage in order, recording progress as it goes."""
    for stage in STAGES:
        handler = STAGE_HANDLERS.get(stage)
        if handler:
            state = handler(state)
    return state


def build_limits(
    depth: str | None = None,
    max_usd: float | None = None,
    max_rounds: int | None = None,
    max_queries: int | None = None,
    max_sources: int | None = None,
) -> dict[str, object]:
    """Resolve run limits from the requested depth and explicit overrides (FR-IN-3)."""
    resolved_depth = (depth or settings.budget.default_depth).lower()
    if resolved_depth not in settings.budget.depth_max_rounds:
        resolved_depth = "standard"

    budget = settings.budget
    limits: dict[str, object] = {
        "depth": resolved_depth,
        "max_usd": float(
            min(max_usd, budget.max_usd_ceiling)
            if max_usd is not None
            else budget.default_max_usd
        ),
        "max_debate_rounds": int(max_rounds or budget.depth_max_rounds[resolved_depth]),
        "max_panel_rounds": int(budget.depth_max_rounds[resolved_depth] + 1),
        "max_wall_seconds": 3600,
        "max_queries": int(max_queries or budget.depth_max_queries[resolved_depth]),
        "max_sources": int(max_sources or budget.depth_max_sources[resolved_depth]),
    }
    return limits


def start_run(
    domain: str,
    question: str,
    progress_callback: ProgressCallback | None = None,
    model_provider: str | None = None,
    model_name: str | None = None,
    api_key: str | None = None,
    mode: str | None = None,
    depth: str | None = None,
    max_usd: float | None = None,
    max_rounds: int | None = None,
    max_queries: int | None = None,
    max_sources: int | None = None,
) -> ResearchState:
    """Run an investigation for a domain and question.

    ``mode`` selects Problem mode (the default) or Topic Discovery mode. When
    the mode is omitted the intake classifier decides, which is what makes
    "describe a pain point or just a topic" work without a mode switch.
    """
    initial_state: ResearchState = {
        "run_id": str(uuid4()),
        "domain": domain,
        "question": question,
        "mode": mode or "auto",
        "limits": build_limits(depth, max_usd, max_rounds, max_queries, max_sources),
        "spend": {"usd": 0.0, "tokens": 0, "calls": 0, "tool_calls": 0},
        "current_stage": "intake",
        "round": 1,
        "attempt": 1,
        "max_attempts": settings.workflow.max_attempts,
        "tool_calls": 0,
        "audit": [],
        "status": "running",
        "intake": {},
        "clarifying_questions": [],
        "scope": {},
        "pain_points": [],
        "transcript": [],
        "panel_round": 0,
        "convergence": 0.0,
        "problem_candidates": [],
        "selected_problem_ids": [],
        "evidence": [],
        "gaps": [],
        "ideas": [],
        "critiques": [],
        "lineage": [],
        "validation_results": [],
        "ranked_ideas": [],
        "checkpoints": [],
        "pending_checkpoint": None,
        "claims": [],
        "sources": [],
        "subagent_executions": [],
        "citation_verifications": [],
        "disagreements": [],
        "projections": [],
        "brainstormed_ideas": [],
        "overcome_strategies": [],
        "attempt_history": [],
        "provider_failures": [],
        "model_provider": model_provider,
        "model_name": model_name,
        "api_key": api_key,
    }
    if progress_callback:
        initial_state["progress_callback"] = progress_callback

    result = _dispatch(initial_state)
    completed_state = {**initial_state, **result}
    completed_state.pop("progress_callback", None)
    completed_state.pop("api_key", None)
    return cast(ResearchState, completed_state)


def _dispatch(state: ResearchState) -> ResearchState:
    """Route the run to Problem mode or Topic Discovery mode.

    ``auto`` (or an absent mode) runs the intake classifier, which decides
    whether the input is a problem or a topic and asks for clarification when
    it cannot tell.
    """
    requested_mode = state.get("mode")
    if requested_mode in {"problem", "topic"}:
        resolved = requested_mode
    else:
        classify_intake(state)
        intake = state.get("intake") or {}
        resolved = str(intake.get("mode") or "problem")
        if resolved == "ambiguous":
            resolved = str(intake.get("assumed_mode") or "topic")

    state["mode"] = resolved

    if resolved == "topic":
        from .discovery import run_discovery

        _emit(
            state,
            {
                "type": "mode_selected",
                "stage": "intake",
                "title": "Topic Discovery mode",
                "detail": "Discovering the problems worth solving before research begins.",
                "mode": "topic",
            },
        )
        run_discovery(state)
        state["status"] = "awaiting_input"
        _emit(
            state,
            {
                "type": "checkpoint_requested",
                "stage": "problem_selection",
                "kind": "discovery_selection",
                "title": "You decide which problems to research",
                "detail": "Select, edit or merge the problems the panel surfaced.",
                "candidates": state.get("problem_candidates") or [],
            },
        )
        return state

    _emit(
        state,
        {
            "type": "mode_selected",
            "stage": "intake",
            "title": "Problem mode",
            "detail": "Researching a specific problem end to end.",
            "mode": "problem",
        },
    )
    return _run_pipeline(state)
