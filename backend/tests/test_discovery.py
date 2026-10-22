"""Tests for the Topic Discovery subgraph and the role routing it depends on."""

from __future__ import annotations

import pytest

from app.discovery import (
    _fallback_pain_points,
    _fallback_position,
    _fallback_stance,
    mine_pain_points,
    panel_round,
    plan_scans,
    run_discovery,
    scope_topic,
    synthesize_problems,
)
from app.roles import PANEL_PERSONAS, estimate_cost_usd, resolve_model, resolve_role


SOURCE = {
    "id": "source-1",
    "url": "https://example.org/a",
    "title": "Grid storage limits",
    "publisher": "example.org",
    "content": (
        "Degradation of cell chemistry remains a limitation for grid storage. "
        "Cycle life cannot be predicted from early data, and a safety constraint "
        "still limits deployment in dense urban sites."
    ),
    "excerpt": "short",
}


def test_role_routing_uses_the_models_config() -> None:
    """FR-PF-1: the skeptic must not share a tier with the ideators."""
    assert resolve_role("skeptic") == "critic"
    assert resolve_role("novelty_checker") == "critic"
    assert resolve_role("ideator") == "creative"
    assert resolve_role("landscape_scout") == "fast"
    # Unlisted agents fall back to the reasoning tier.
    assert resolve_role("some_new_agent") == "reason"

    spec = resolve_model("skeptic")
    assert spec["tier"] == "critic"
    assert spec["temperature"] <= 0.3


def test_cost_estimate_scales_with_prompt_size() -> None:
    cheap, cheap_tokens = estimate_cost_usd("groq", 1000, 1000)
    rich, rich_tokens = estimate_cost_usd("anthropic", 1000, 1000)
    assert rich > cheap
    assert rich_tokens == cheap_tokens

    free, _ = estimate_cost_usd("ollama", 4000, 4000)
    assert free == 0.0


def test_fallback_pain_points_quote_real_limitations() -> None:
    """Without a model the miner must still cite retrieved text, not invent it."""
    findings = _fallback_pain_points([SOURCE])
    assert findings, "expected a limitation sentence to be extracted"
    assert all(finding["evidence_ids"] == ["source-1"] for finding in findings)
    assert all(finding["cite_labels"] for finding in findings)
    assert all(finding["extracted"] for finding in findings)


def test_fallback_pain_points_ignore_text_without_limitations() -> None:
    clean = {
        "id": "s2",
        "title": "News",
        "content": "The company reported revenue growth of twelve percent this quarter.",
    }
    assert _fallback_pain_points([clean]) == []


def test_fallback_stance_follows_the_persona_mandate() -> None:
    by_id = {persona.id: persona for persona in PANEL_PERSONAS}
    assert _fallback_stance(by_id["contrarian"]) == "challenge"
    assert _fallback_stance(by_id["academic"]) == "defend"
    assert _fallback_stance(by_id["practitioner"]) == "support"
    assert _fallback_stance(by_id["futurist"]) == "question"


def test_fallback_position_cites_the_evidence() -> None:
    by_id = {persona.id: persona for persona in PANEL_PERSONAS}
    point = {"text": "cycle life cannot be predicted", "cite_labels": ["E1"], "cluster": "degradation"}
    for persona in PANEL_PERSONAS:
        position = _fallback_position(persona, point, [point])
        assert "E1" in position
        assert len(position) > 40


def test_scope_topic_fills_subtopics_without_a_model(monkeypatch) -> None:
    monkeypatch.setattr("app.workflow.call_role_llm_json", lambda *a, **k: None)
    state: dict = {"domain": "grid storage", "question": "tell me about it"}
    scope_topic(state)
    scope = state["scope"]
    assert scope["subtopics"] == ["grid storage"]
    assert scope["search_queries"], "a fallback query set must exist"
    assert scope["framing"]


def test_mine_pain_points_falls_back_to_quotes(monkeypatch) -> None:
    monkeypatch.setattr("app.workflow.call_role_llm_json", lambda *a, **k: None)
    state: dict = {"sources": [SOURCE], "current_stage": "mine_pain_points"}
    mine_pain_points(state)
    assert state["pain_points"], "the miner must still produce evidence-linked pain points"
    assert state["pain_points"][0]["evidence_ids"] == ["source-1"]


def test_panel_round_records_a_turn_per_persona(monkeypatch) -> None:
    monkeypatch.setattr("app.workflow.call_role_llm_json", lambda *a, **k: None)
    state: dict = {
        "sources": [SOURCE],
        "pain_points": [
            {
                "id": "p1",
                "text": "cycle life cannot be predicted",
                "cluster": "degradation",
                "severity": 0.6,
                "evidence_ids": ["source-1"],
                "cite_labels": ["E1"],
            }
        ],
        "transcript": [],
        "current_stage": "panel_round",
    }
    panel_round(state)
    transcript = state["transcript"]
    # One turn per persona plus the moderator.
    assert len(transcript) == len(PANEL_PERSONAS) + 1
    assert transcript[-1]["is_moderator"] is True
    assert all(turn["position"] for turn in transcript)
    assert state["panel_round"] == 1
    assert 0.0 <= state["convergence"] <= 1.0


def test_synthesize_problems_promotes_pain_points_without_a_model(monkeypatch) -> None:
    monkeypatch.setattr("app.workflow.call_role_llm_json", lambda *a, **k: None)
    state: dict = {
        "sources": [SOURCE],
        "pain_points": [
            {
                "id": "p1",
                "text": "cycle life cannot be predicted from early data",
                "cluster": "degradation",
                "severity": 0.7,
                "evidence_ids": ["source-1"],
                "cite_labels": ["E1"],
            }
        ],
        "transcript": [],
        "current_stage": "problem_synthesis",
    }
    synthesize_problems(state)
    candidates = state["problem_candidates"]
    assert candidates, "problems must still be produced without a model"
    assert candidates[0]["evidence_ids"] == ["source-1"]
    assert candidates[0]["extracted"] is True
    assert candidates[0]["rank"] == 1


def test_run_discovery_reaches_the_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr("app.discovery.search_web", lambda *a, **k: [SOURCE])
    monkeypatch.setattr("app.workflow.call_role_llm_json", lambda *a, **k: None)
    state: dict = {
        "domain": "grid storage",
        "question": "tell me about grid storage",
        "sources": [],
        "transcript": [],
        "pain_points": [],
        "limits": {"max_sources": 3, "max_panel_rounds": 1},
        "current_stage": "intake",
    }
    run_discovery(state)
    assert state["pain_points"]
    assert state["transcript"]
    assert state["problem_candidates"]
    assert state["convergence"] >= 0.0


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
def test_depth_changes_the_limits(depth: str) -> None:
    from app.workflow import build_limits

    limits = build_limits(depth, 3.0)
    assert limits["depth"] == depth
    assert limits["max_usd"] == 3.0
    assert limits["max_sources"] > 0
    assert limits["max_queries"] > 0


def test_landscape_scan_respects_the_query_budget(monkeypatch) -> None:
    """D2 must not search more angles than the run allows.

    The model proposes up to ten queries. Without trimming to the run's
    `max_queries`, the scan ran every proposal and blew through the time
    budget. Each search also used to fan out into three derived queries, so a
    loop over N queries issued N x 3 searches.
    """
    calls: list[list] = []

    def fake_search(domain, question, progress_callback=None, queries=None):
        calls.append(queries or [])
        return []

    monkeypatch.setattr("app.discovery.search_web", fake_search)
    state: dict = {
        "domain": "grid storage",
        "question": "tell me about it",
        "sources": [],
        "limits": {"max_queries": 2, "max_sources": 4},
        "scope": {
            "topic": "grid storage",
            "search_queries": [f"angle {i}" for i in range(9)],
        },
        "current_stage": "landscape_scan",
    }

    plan_scans(state)

    assert len(calls) <= 2, f"the scan exceeded the query budget: {len(calls)} searches"
    for query_set in calls:
        assert len(query_set) == 1, "each search must issue exactly one query"


def test_landscape_scan_keeps_a_limitation_angle(monkeypatch) -> None:
    """The limitation query carries the problem signal and must survive the trim."""
    calls: list[list] = []

    def fake_search(domain, question, progress_callback=None, queries=None):
        calls.append(queries or [])
        return []

    monkeypatch.setattr("app.discovery.search_web", fake_search)
    state: dict = {
        "domain": "grid storage",
        "question": "tell me about it",
        "sources": [],
        "limits": {"max_queries": 2, "max_sources": 4},
        "scope": {
            "topic": "grid storage",
            "search_queries": ["angle one", "angle two", "angle three"],
        },
        "current_stage": "landscape_scan",
    }

    plan_scans(state)

    issued = [item[0] for call in calls for item in call]
    assert any("limitation" in query.casefold() for query in issued), issued
