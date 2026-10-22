"""Topic Discovery subgraph (PRD stage D1 to D6, FR-DS-1 to FR-DS-7).

Topic mode lets a user arrive with a curiosity instead of a problem. The
subgraph scopes the topic, scans the landscape, mines pain points, runs a
multi-round panel debate with a moderator, and synthesises ranked problem
statements. The problems it produces are the same shape the research pipeline
consumes, so both modes converge on one evidence standard.
"""

from __future__ import annotations

import re
from typing import Any, Callable
from uuid import uuid4

from .config import settings
from .roles import MODERATOR, PANEL_PERSONAS, Persona
from .sources import SearchProviderError, search_web


ProgressCallback = Callable[[dict[str, object]], None]

SOURCE_TYPE_HINTS: tuple[tuple[str, str], ...] = (
    ("paper", "research paper preprint journal conference study"),
    ("repo", "github repository code implementation issue library"),
    ("forum", "forum discussion community stack overflow reddit question"),
    ("news", "news announcement press industry report"),
    ("benchmark", "benchmark dataset evaluation results comparison"),
)


def _emit(state: dict[str, Any], event: dict[str, object]) -> None:
    callback = state.get("progress_callback")
    if callback:
        callback(event)
    stage = str(event.get("stage", state.get("current_stage", "discovery")))
    detail = str(event.get("detail", event.get("title", "")))
    event_name = str(event.get("type", "progress"))
    state.setdefault("audit", []).append({"stage": stage, "event": event_name, "detail": detail})


def _speak(
    state: dict[str, Any],
    persona: Persona,
    position: str,
    round_index: int,
    cites: list[str],
    turn: dict[str, Any] | None = None,
) -> None:
    """Record one panel turn and announce the current speaker."""
    state["active_speaker"] = {
        "id": persona.id,
        "name": persona.name,
        "role": persona.mandate,
        "speech": position,
        "stage": "panel",
    }
    _emit(
        state,
        {
            "type": "panel_turn",
            "stage": "panel",
            "speaker_id": persona.id,
            "speaker_name": persona.name,
            "round": round_index,
            "speech": position,
            "detail": position,
            "panel_turn": turn,
        },
    )

def _digest(sources: list[dict[str, Any]], limit: int = 9000) -> str:
    """Render retrieved evidence into a bounded digest for the panel to read."""
    blocks: list[str] = []
    used = 0
    for index, source in enumerate(sources):
        text = str(source.get("content") or source.get("excerpt") or "").strip()
        if not text:
            continue
        block = f"[E{index + 1}] {source.get('title', 'Untitled')} | {source.get('publisher') or 'unknown'}\n{text}"
        if used + len(block) > limit:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks) if blocks else "(no retrieved evidence available yet)"


def _evidence_index(sources: list[dict[str, Any]]) -> dict[str, str]:
    """Map source position to its stable evidence id (E1, E2, ...)."""
    return {f"E{index + 1}": str(source.get("id", "")) for index, source in enumerate(sources)}


# Phrases that mark a stated limitation in the source text. This is the
# evidence-only fallback: it finds real sentences from retrieved pages and
# links them back to the page they came from.
_LIMITATION_MARKERS = (
    "limitation",
    "challenge",
    "difficult",
    "bottleneck",
    "struggle",
    "cannot",
    "can not",
    "unable",
    "remains open",
    "open problem",
    "future work",
    "gap in",
    "lacks",
    "suffer from",
    "barrier",
    "constraint",
    "drawback",
    "shortcoming",
)


def _fallback_pain_points(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract limitation sentences from retrieved text without a model.

    Every returned pain point points at a real retrieved source. It is not a
    synthesis, it is a quote, and the UI labels it as such.
    """
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source_index, source in enumerate(sources):
        text = str(source.get("content") or source.get("excerpt") or "")
        if not text:
            continue
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        for sentence in sentences:
            lowered = sentence.casefold()
            if len(sentence) < 40 or len(sentence) > 400:
                continue
            if not any(marker in lowered for marker in _LIMITATION_MARKERS):
                continue
            fingerprint = lowered[:120]
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            findings.append(
                {
                    "id": str(uuid4()),
                    "text": sentence,
                    "cluster": "stated limitation",
                    "severity": 0.4,
                    "evidence_ids": [str(source.get("id", ""))],
                    "cite_labels": [f"E{source_index + 1}"],
                    "extracted": True,
                }
            )
            if len(findings) >= settings.discovery.max_pain_points:
                return findings
    return findings


# --- D1: Topic scoping -------------------------------------------------------


def scope_topic(state: dict[str, Any]) -> dict[str, Any]:
    """D1 — clarify the topic, set boundaries, generate sub-topics and vocabulary."""
    state["current_stage"] = "scope_topic"
    topic = state.get("domain") or state.get("question", "")
    _emit(
        state,
        {
            "type": "discovery_scope_started",
            "stage": "scope_topic",
            "detail": f"Scoping the topic: {topic}",
        },
    )

    scope: dict[str, Any] = {
        "topic": topic,
        "subtopics": [],
        "keywords": [],
        "boundaries": "",
        "search_queries": [],
        "source_types": [hint for _, hint in SOURCE_TYPE_HINTS],
        "framing": "Topic Discovery mode: problems are discovered before research begins.",
    }

    from .workflow import call_role_llm_json  # local import avoids a cycle

    payload = call_role_llm_json(
        state,
        "scoper",
        f"""Scope this research topic into concrete sub-topics and search vocabulary.

TOPIC: {topic}
USER CONTEXT: {state.get("question", "")}

Respond with JSON:
{{
  "framing": "one sentence on what this topic really covers",
  "subtopics": ["up to {settings.discovery.max_subtopics} specific sub-topics"],
  "keywords": ["10 to 20 search keywords and technical terms"],
  "boundaries": "what is out of scope for this investigation",
  "search_queries": ["6 to 10 distinct search queries covering different angles"]
}}""",
    )

    if payload:
        scope["framing"] = str(payload.get("framing") or scope["framing"])
        scope["subtopics"] = [str(item) for item in (payload.get("subtopics") or [])][
            : settings.discovery.max_subtopics
        ]
        scope["keywords"] = [str(item) for item in (payload.get("keywords") or [])][:20]
        scope["boundaries"] = str(payload.get("boundaries") or "")
        scope["search_queries"] = [str(item) for item in (payload.get("search_queries") or [])][:10]

    if not scope["subtopics"]:
        scope["subtopics"] = [topic]
    if not scope["search_queries"]:
        scope["search_queries"] = [
            f"{topic} {keyword}" for keyword in (scope["keywords"][:5] or ["research", "limitations"])
        ]

    state["scope"] = scope
    _emit(
        state,
        {
            "type": "discovery_scope_ready",
            "stage": "scope_topic",
            "title": f"{len(scope['subtopics'])} sub-topics scoped",
            "detail": " · ".join(scope["subtopics"][:5]),
        },
    )
    return state


# --- D2: Landscape scan ------------------------------------------------------


def plan_scans(state: dict[str, Any]) -> dict[str, Any]:
    """D2 — run parallel web and scholarly search across multiple source types."""
    state["current_stage"] = "landscape_scan"
    scope = state.get("scope") or {}
    limits = state.get("limits") or {}
    topic = str(scope.get("topic") or state.get("domain") or "")

    # The run's query budget is a hard limit. The model proposes more angles
    # than the budget allows, so the list is trimmed to fit. Without this the
    # scan would run every proposed query and blow through the time budget.
    max_queries = int(limits.get("max_queries", settings.search.max_queries))
    queries: list[str] = list(scope.get("search_queries") or [])[:max_queries]

    if not queries:
        queries = [
            f"{topic} limitations",
            f"{topic} open problems",
            f"{topic} state of the art review",
        ][:max_queries]

    # Always include at least one query that targets the limitation language
    # the pain-point miner looks for. Without it the scan only surfaces paper
    # abstracts, which open with a topic sentence rather than a problem.
    limitation_query = f"{topic} limitations challenges open problems"
    if not any("limitation" in query.casefold() for query in queries):
        queries = [limitation_query] + queries[: max(0, max_queries - 1)]
    queries = queries[:max_queries]

    _emit(
        state,
        {
            "type": "discovery_scan_started",
            "stage": "landscape_scan",
            "detail": f"Scanning {len(queries)} angles across the landscape",
        },
    )

    sources: list[dict[str, Any]] = list(state.get("sources") or [])
    seen_urls: set[str] = {str(source.get("url", "")) for source in sources}
    max_sources = int(state.get("limits", {}).get("max_sources", settings.search.max_sources))

    # Collect candidates from every angle first, then cap. Stopping the scan
    # the moment the source cap is hit would let the first query crowd out the
    # limitation query, which is the one carrying the problem signal.
    candidates: list[tuple[dict[str, Any], str]] = []
    candidate_urls: set[str] = set(seen_urls)

    for query in queries:
        try:
            found = search_web(
                topic,
                query,
                progress_callback=state.get("progress_callback"),
                queries=[(query, None)],
            )
        except SearchProviderError as error:
            _emit(
                state,
                {
                    "type": "discovery_scan_partial",
                    "stage": "landscape_scan",
                    "detail": f"{query}: {error}",
                },
            )
            continue
        for source in found:
            url = str(source.get("url", ""))
            if not url or url in candidate_urls:
                continue
            candidate_urls.add(url)
            source.setdefault("discovery_query", query)
            candidates.append((source, query))

    # The limitation angle is searched last but is the most valuable, so give
    # its results a reserved share of the budget.
    limitation_candidates = [item for item in candidates if "limitation" in item[1].casefold()]
    other_candidates = [item for item in candidates if "limitation" not in item[1].casefold()]
    reserved = max(1, max_sources // 2) if limitation_candidates else 0
    ordered = limitation_candidates[:reserved] + other_candidates
    ordered += limitation_candidates[reserved:]

    for source, query in ordered:
        if len(sources) >= max_sources:
            break
        sources.append(source)

    state["sources"] = sources
    _emit(
        state,
        {
            "type": "discovery_scan_ready",
            "stage": "landscape_scan",
            "title": f"{len(sources)} sources across {len(queries)} angles",
            "detail": f"{len(sources)} pages retrieved for the landscape scan",
        },
    )
    return state


# --- D3: Pain-point mining ---------------------------------------------------


def mine_pain_points(state: dict[str, Any]) -> dict[str, Any]:
    """D3 — extract stated limitations, open problems and failure cases."""
    state["current_stage"] = "mine_pain_points"
    sources = state.get("sources") or []
    digest = _digest(sources)

    _emit(
        state,
        {
            "type": "discovery_mining_started",
            "stage": "mine_pain_points",
            "detail": "Extracting stated limitations and open problems",
        },
    )

    from .workflow import call_role_llm_json

    payload = call_role_llm_json(
        state,
        "pain_point_miner",
        f"""Mine the evidence below for real pain points: stated limitations, open problems,
failure cases, future-work directions and recurring complaints.

EVIDENCE:
{digest}

Respond with JSON:
{{
  "pain_points": [
    {{
      "text": "the pain point, stated as a concrete problem",
      "cluster": "a short thematic cluster name",
      "severity": 0.0 to 1.0,
      "cites": ["E1", "E4"]
    }}
  ]
}}
Only report pain points that the evidence actually supports. Cite the evidence ids.
Return at most {settings.discovery.max_pain_points} pain points.""",
    )

    index = _evidence_index(sources)
    pain_points: list[dict[str, Any]] = []
    for entry in (payload or {}).get("pain_points", []) or []:
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("text") or "").strip()
        if not text:
            continue
        cites = [str(item) for item in (entry.get("cites") or []) if str(item) in index]
        pain_points.append(
            {
                "id": str(uuid4()),
                "text": text[:600],
                "cluster": str(entry.get("cluster") or "unclustered")[:120],
                "severity": max(0.0, min(1.0, float(entry.get("severity") or 0.0))),
                "evidence_ids": [index[cite] for cite in cites],
                "cite_labels": cites,
            }
        )
        if len(pain_points) >= settings.discovery.max_pain_points:
            break

    if not pain_points and sources:
        # No model: fall back to quoting real limitation sentences from the
        # retrieved pages so the panel still has evidence to debate.
        pain_points = _fallback_pain_points(sources)

    state["pain_points"] = pain_points
    if not pain_points:
        _emit(
            state,
            {
                "type": "discovery_mining_empty",
                "stage": "mine_pain_points",
                "title": "No pain points could be extracted",
                "detail": (
                    "Pain-point mining needs a model provider. The retrieved sources are still in the "
                    "evidence vault and can be reviewed directly."
                ),
            },
        )
    _emit(
        state,
        {
            "type": "discovery_mining_ready",
            "stage": "mine_pain_points",
            "title": f"{len(pain_points)} pain points clustered",
            "detail": f"{len({point['cluster'] for point in pain_points})} clusters identified",
        },
    )
    return state


# --- D4: Panel discussion ----------------------------------------------------


def panel_round(state: dict[str, Any]) -> dict[str, Any]:
    """D4 — one round of persona debate, followed by a moderator summary."""
    state["current_stage"] = "panel_round"
    round_index = int(state.get("panel_round", 0)) + 1
    state["panel_round"] = round_index

    sources = state.get("sources") or []
    pain_points = state.get("pain_points") or []
    transcript = state.get("transcript") or []
    digest = _digest(sources, limit=7000)
    index = _evidence_index(sources)

    pain_text = "\n".join(
        f"- {point['text']} (cluster: {point['cluster']}, severity {point.get('severity', 0):.2f})"
        for point in pain_points[:20]
    ) or "(no pain points extracted yet)"

    prior_text = "\n".join(
        f"{turn.get('persona')}: {turn.get('position')}" for turn in transcript[-12:]
    ) or "(this is the first round)"

    _emit(
        state,
        {
            "type": "panel_round_started",
            "stage": "panel_round",
            "round": round_index,
            "detail": f"Round {round_index} of {settings.discovery.max_panel_rounds}",
        },
    )

    from .workflow import call_role_llm_json

    spoken = 0
    for persona in PANEL_PERSONAS:
        payload = call_role_llm_json(
            state,
            "panel_persona",
            f"""You are the {persona.name} on a research panel. Your mandate: {persona.mandate}

This is round {round_index}. Every position must cite evidence ids (E1, E2, ...) or be
explicitly marked as opinion. An empty citation list is allowed only for a stated opinion.

PAIN POINTS ON THE TABLE:
{pain_text}

EVIDENCE:
{digest}

WHAT THE PANEL SAID SO FAR:
{prior_text}

Respond with JSON:
{{
  "position": "2 to 4 sentences stating your position",
  "cites": ["E1", "E7"],
  "stance": "support" | "challenge" | "defend" | "question" | "neutral",
  "challenges": ["persona id you are challenging"]
}}""",
        )
        if not payload:
            continue
        position = str(payload.get("position") or "").strip()
        if not position:
            continue
        cites = [str(item) for item in (payload.get("cites") or []) if str(item) in index]
        stance = str(payload.get("stance") or "neutral")
        if stance not in {"support", "challenge", "defend", "question", "neutral"}:
            stance = "neutral"
        challenges = [str(item) for item in (payload.get("challenges") or []) if item]

        turn = {
            "id": str(uuid4()),
            "round": round_index,
            "persona": persona.name,
            "persona_id": persona.id,
            "initials": persona.initials,
            "color": persona.color,
            "position": position[:1400],
            "cites": cites,
            "cite_labels": cites,
            "evidence_ids": [index[cite] for cite in cites],
            "challenges": challenges,
            "stance": stance,
            "status": "done",
        }
        transcript.append(turn)
        spoken += 1
        _speak(state, persona, turn["position"], round_index, cites, turn)

    if not spoken and pain_points:
        # No model: each persona reads the evidence and states a position
        # grounded in it. The stance still differs per mandate, and every
        # statement cites the pain point it is based on.
        for offset, persona in enumerate(PANEL_PERSONAS):
            point = pain_points[(offset + round_index - 1) % len(pain_points)]
            cites = list(point.get("cite_labels") or [])
            position = _fallback_position(persona, point, pain_points)
            turn = {
                "id": str(uuid4()),
                "round": round_index,
                "persona": persona.name,
                "persona_id": persona.id,
                "initials": persona.initials,
                "color": persona.color,
                "position": position,
                "cites": cites,
                "cite_labels": cites,
                "evidence_ids": list(point.get("evidence_ids") or []),
                "challenges": [],
                "stance": _fallback_stance(persona),
                "status": "done",
                "extracted": True,
            }
            transcript.append(turn)
            _speak(state, persona, position, round_index, cites, turn)

    # --- Moderator summarises and scores convergence ---
    panel_text = "\n".join(
        f"{turn['persona']} ({turn['stance']}): {turn['position']}" for turn in transcript[-8:]
    )
    moderator_payload = call_role_llm_json(
        state,
        "moderator",
        f"""You moderate this research panel. Summarise the round, judge how close the panel
is to agreement, and state exactly what remains disputed.

PANEL STATEMENTS THIS ROUND:
{panel_text}

Respond with JSON:
{{
  "summary": "2 to 3 sentences: what the round settled and what is still contested",
  "convergence": 0.0 to 1.0,
  "unresolved": ["the open disagreement"]
}}""",
    )

    convergence = 0.0
    if moderator_payload:
        convergence = max(0.0, min(1.0, float(moderator_payload.get("convergence") or 0.0)))
        summary = str(moderator_payload.get("summary") or "").strip()
        unresolved = [str(item) for item in (moderator_payload.get("unresolved") or [])]
        if summary:
            turn = {
                "id": str(uuid4()),
                "round": round_index,
                "persona": MODERATOR.name,
                "persona_id": MODERATOR.id,
                "initials": MODERATOR.initials,
                "color": MODERATOR.color,
                "position": summary[:1400],
                "cites": [],
                "cite_labels": [],
                "evidence_ids": [],
                "challenges": [],
                "stance": "neutral",
                "status": "done",
                "is_moderator": True,
            }
            transcript.append(turn)
            _speak(state, MODERATOR, turn["position"], round_index, [], turn)
    elif transcript:
        # No moderator model: summarise the round from the turns themselves.
        agree = sum(1 for turn in transcript if turn.get("stance") in {"support", "defend"})
        total = max(1, len(transcript))
        convergence = round(agree / total, 2)
        clusters = {str(turn.get("cluster") or "open") for turn in pain_points[:8]}
        summary = (
            f"Round {round_index} surfaced {len(transcript)} statements across {len(clusters)} problem "
            f"cluster(s). {agree} of {total} positions leaned toward the current framing. "
            f"No model moderator was available, so this summary is computed from the panel's own "
            f"stances rather than a synthesis. Next focus: rank the clusters that carry the most evidence."
        )
        turn = {
            "id": str(uuid4()),
            "round": round_index,
            "persona": MODERATOR.name,
            "persona_id": MODERATOR.id,
            "initials": MODERATOR.initials,
            "color": MODERATOR.color,
            "position": summary[:1400],
            "cites": [],
            "cite_labels": [],
            "evidence_ids": [],
            "challenges": [],
            "stance": "neutral",
            "status": "done",
            "is_moderator": True,
            "computed": True,
        }
        transcript.append(turn)
        _speak(state, MODERATOR, turn["position"], round_index, [], turn)

    state["transcript"] = transcript
    state["convergence"] = convergence
    _emit(
        state,
        {
            "type": "panel_round_ready",
            "stage": "panel_round",
            "round": round_index,
            "convergence_score": convergence,
            "title": f"Round {round_index}: convergence {convergence:.2f}",
            "detail": f"{len(transcript)} panel statements so far",
        },
    )
    return state


def _fallback_stance(persona: Persona) -> str:
    """A stance that follows from the persona's mandate, used when no model speaks."""
    if persona.id == "contrarian":
        return "challenge"
    if persona.id == "academic":
        return "defend"
    if persona.id == "practitioner":
        return "support"
    if persona.id == "futurist":
        return "question"
    return "neutral"


def _fallback_position(
    persona: Persona,
    point: dict[str, Any],
    pain_points: list[dict[str, Any]],
) -> str:
    """Write a short, honest position from the persona's point of view."""
    text = str(point.get("text") or "").strip()
    cites = ", ".join(point.get("cite_labels") or []) or "the retrieved sources"
    cluster = str(point.get("cluster") or "this area")
    others = len(pain_points)

    if persona.id == "practitioner":
        return (
            f"From operating experience, the binding constraint is that {text} "
            f"That is where teams actually lose time and money. Cited: {cites}."
        )
    if persona.id == "academic":
        return (
            f"The published record is explicit here: {text} "
            f"I would not accept a solution that does not first reproduce this. Cited: {cites}."
        )
    if persona.id == "strategist":
        return (
            f"I read {others} open problem(s) in this cluster. The one worth funding is that {text} "
            f"It is tractable without waiting on new infrastructure. Cited: {cites}."
        )
    if persona.id == "contrarian":
        return (
            f"I am not convinced this is the real blocker. The claim is that {text} "
            f"That may be overstated — worth checking whether the constraint is actually {cluster}. "
            f"Cited: {cites}."
        )
    if persona.id == "futurist":
        return (
            f"This framing is likely to age badly. While the field treats {text} as settled, "
            f"adjacent technologies are already changing what counts as the constraint. Cited: {cites}."
        )
    return f"Retrieved evidence states: {text} Cited: {cites}."


# --- D5: Problem synthesis ---------------------------------------------------


def synthesize_problems(state: dict[str, Any]) -> dict[str, Any]:
    """D5 — turn the debate into ranked problem statements."""
    state["current_stage"] = "problem_synthesis"
    pain_points = state.get("pain_points") or []
    transcript = state.get("transcript") or []
    sources = state.get("sources") or []
    index = _evidence_index(sources)

    pain_text = "\n".join(
        f"- {point['text']} (cluster: {point['cluster']}, severity {point.get('severity', 0):.2f})"
        for point in pain_points[:24]
    ) or "(no pain points)"

    panel_text = "\n".join(
        f"{turn['persona']} ({turn['stance']}): {turn['position']}" for turn in transcript[-12:]
    ) or "(no panel transcript)"

    _emit(
        state,
        {
            "type": "problem_synthesis_started",
            "stage": "problem_synthesis",
            "detail": "Ranking the problems the panel surfaced",
        },
    )

    from .workflow import call_role_llm_json

    payload = call_role_llm_json(
        state,
        "problem_synthesizer",
        f"""Synthesise the panel's work into ranked problem statements for a research council.

PAIN POINTS:
{pain_text}

PANEL TRANSCRIPT:
{panel_text}

Respond with JSON:
{{
  "problems": [
    {{
      "statement": "the problem, stated so an engineer could act on it",
      "why_it_matters": "why solving it is worth the effort",
      "severity": 0.0 to 1.0,
      "tractability": 0.0 to 1.0,
      "gap_size": 0.0 to 1.0,
      "cites": ["E1", "E3"]
    }}
  ]
}}
Rank by combined severity, tractability and gap size. Return at most
{settings.discovery.max_problem_candidates} problems. Each must cite evidence ids.""",
    )

    candidates: list[dict[str, Any]] = []
    for entry in (payload or {}).get("problems", []) or []:
        if not isinstance(entry, dict):
            continue
        statement = str(entry.get("statement") or "").strip()
        if not statement:
            continue
        cites = [str(item) for item in (entry.get("cites") or []) if str(item) in index]
        if len(cites) < settings.discovery.min_evidence_per_problem:
            continue
        severity = max(0.0, min(1.0, float(entry.get("severity") or 0.0)))
        tractability = max(0.0, min(1.0, float(entry.get("tractability") or 0.0)))
        gap_size = max(0.0, min(1.0, float(entry.get("gap_size") or 0.0)))
        candidates.append(
            {
                "id": str(uuid4()),
                "statement": statement[:800],
                "why_it_matters": str(entry.get("why_it_matters") or "")[:800],
                "evidence_ids": [index[cite] for cite in cites],
                "cite_labels": cites,
                "severity": severity,
                "tractability": tractability,
                "gap_size": gap_size,
                "cluster": "discovered",
                "rank": len(candidates) + 1,
                "status": "candidate",
                "origin": "discovery",
                "score": round((severity * 0.4 + tractability * 0.25 + gap_size * 0.35), 4),
            }
        )
        if len(candidates) >= settings.discovery.max_problem_candidates:
            break

    candidates.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    for position, candidate in enumerate(candidates, start=1):
        candidate["rank"] = position

    if not candidates and pain_points:
        # No model: promote the highest-severity pain points into problems.
        # They stay labelled as extracted, not synthesised.
        ranked_pain = sorted(pain_points, key=lambda item: float(item.get("severity") or 0.0), reverse=True)
        for point in ranked_pain[: settings.discovery.max_problem_candidates]:
            candidates.append(
                {
                    "id": str(uuid4()),
                    "statement": str(point.get("text", ""))[:800],
                    "why_it_matters": "Stated as a limitation by a retrieved source.",
                    "evidence_ids": list(point.get("evidence_ids") or []),
                    "cite_labels": list(point.get("cite_labels") or []),
                    "severity": float(point.get("severity") or 0.0),
                    "tractability": 0.0,
                    "gap_size": 0.0,
                    "cluster": str(point.get("cluster") or "extracted"),
                    "rank": len(candidates) + 1,
                    "status": "candidate",
                    "origin": "discovery",
                    "score": float(point.get("severity") or 0.0),
                    "extracted": True,
                }
            )

    state["problem_candidates"] = candidates
    _emit(
        state,
        {
            "type": "problem_synthesis_ready",
            "stage": "problem_synthesis",
            "title": f"{len(candidates)} ranked problems",
            "detail": (
                f"Top: {candidates[0]['statement'][:140]}" if candidates else "No problems met the evidence bar"
            ),
        },
    )
    return state


# --- Orchestration ------------------------------------------------------------


def run_discovery(state: dict[str, Any]) -> dict[str, Any]:
    """Execute D1 to D5, then leave the run awaiting the D6 human checkpoint."""
    scope_topic(state)
    plan_scans(state)
    mine_pain_points(state)

    max_rounds = int(state.get("limits", {}).get("max_panel_rounds", settings.discovery.max_panel_rounds))
    for _ in range(max(1, max_rounds)):
        panel_round(state)
        if float(state.get("convergence", 0.0)) >= settings.discovery.convergence_threshold:
            break

    synthesize_problems(state)
    return state
