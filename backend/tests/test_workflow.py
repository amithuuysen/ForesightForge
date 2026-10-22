import json

from app.sources import SearchProviderError
from app.workflow import _stage_verify, start_run


def no_search_results(monkeypatch) -> None:
    monkeypatch.setattr("app.workflow.search_web", lambda *args, **kwargs: [])


def test_verifier_blocks_runs_without_citable_claims(monkeypatch) -> None:
    no_search_results(monkeypatch)
    result = start_run("battery storage", "What changed in grid-scale battery storage?")

    assert result.get("status") == "needs_evidence"
    assert result.get("current_stage") == "validate"
    assert any(event["event"] == "gate_blocked" for event in result.get("audit", []))


def test_verifier_rejects_claims_linked_to_missing_sources() -> None:
    state = {
        "claims": [{"id": "claim-1", "source_ids": ["not-retrieved"]}],
        "sources": [{"id": "retrieved"}],
        "citation_verifications": [
            {"claim_id": "claim-1", "source_id": "not-retrieved"},
        ],
    }

    result = _stage_verify(state)  # type: ignore[arg-type]

    assert result.get("status") == "needs_evidence"
    assert result.get("audit", [])[-1]["event"] == "gate_blocked"


def test_gather_stage_persists_retrieved_sources(monkeypatch) -> None:
    source = {
        "id": "source-1",
        "url": "https://en.wikipedia.org/?curid=42",
        "title": "Grid energy storage",
        "excerpt": "Retrieved source excerpt",
        "retrieved_at": "2026-10-17T00:00:00+00:00",
    }
    monkeypatch.setattr("app.workflow.search_web", lambda *args, **kwargs: [source])

    result = start_run("battery storage", "What changed in grid-scale battery storage?")

    assert result.get("sources", []) == [source]
    gathered_event = next(event for event in result.get("audit", []) if event["event"] == "sources_found")
    assert "public web search" in gathered_event["detail"]
    assert result.get("status") == "needs_evidence"


def test_search_failure_is_audited_and_keeps_run_blocked(monkeypatch) -> None:
    def fail_search(*args: object, **kwargs: object) -> list[dict[str, object]]:
        raise SearchProviderError("search provider unavailable")

    monkeypatch.setattr("app.workflow.search_web", fail_search)

    result = start_run("battery storage", "What changed in grid-scale battery storage?")

    assert result.get("status") == "needs_evidence"
    assert any(event["event"] == "source_search_failed" for event in result.get("audit", []))


def test_run_executes_the_full_rnd_council(monkeypatch) -> None:
    """Every council stage must run and be recorded, even without a model."""
    no_search_results(monkeypatch)

    result = start_run("LLM inference", "How do we reduce inference latency?")

    stages = [event["stage"] for event in result.get("audit", [])]
    for expected in (
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
    ):
        assert expected in stages, f"missing stage: {expected}"
    assert result.get("current_stage") == "validate"


def test_run_records_mode_and_limits(monkeypatch) -> None:
    """FR-IN-3: a run carries its depth and budget so the UI can show them."""
    no_search_results(monkeypatch)

    result = start_run(
        "battery storage",
        "What changed in grid-scale battery storage?",
        mode="problem",
        depth="deep",
        max_usd=2.5,
    )

    limits = result.get("limits") or {}
    assert limits["depth"] == "deep"
    assert limits["max_usd"] == 2.5
    assert result.get("mode") == "problem"


def test_budget_stops_model_calls_once_spent(monkeypatch) -> None:
    """The run must not keep calling the model after the budget is gone."""
    no_search_results(monkeypatch)
    calls: list[str] = []

    def fake_call_llm_json(prompt: str, *args: object, **kwargs: object) -> dict[str, object] | None:
        calls.append(prompt)
        return {"ok": True}

    monkeypatch.setattr("app.workflow.call_llm_json", fake_call_llm_json)
    monkeypatch.setattr("app.workflow.call_role_llm_json", fake_call_llm_json)

    result = start_run(
        "battery storage",
        "What changed in grid-scale battery storage?",
        max_usd=0.0,
    )

    assert result.get("status") == "needs_evidence"
    spend = result.get("spend") or {}
    assert float(spend.get("usd", 0.0)) <= 0.0


def test_topic_mode_runs_discovery_and_waits_for_a_human(monkeypatch) -> None:
    """FR-DS: topic mode discovers problems and stops at the D6 checkpoint."""
    monkeypatch.setattr("app.workflow.search_web", lambda *args, **kwargs: [])
    monkeypatch.setattr("app.discovery.search_web", lambda *args, **kwargs: [])

    result = start_run(
        "grid storage",
        "Tell me about grid-scale battery storage",
        mode="topic",
    )

    assert result.get("mode") == "topic"
    assert result.get("status") == "awaiting_input"
    events = [event["event"] for event in result.get("audit", [])]
    assert "discovery_scope_started" in events
    assert "discovery_scan_started" in events
    assert "discovery_mining_started" in events
    assert "panel_round_started" in events
    assert "problem_synthesis_started" in events
    assert "checkpoint_requested" in events


def _install_fake_provider(monkeypatch, responder):
    """Patch the HTTP call the provider registry uses.

    This exercises the real spend accounting and failure tracking instead of
    stubbing the workflow helpers, which would skip both. The provider
    resolution is restored because the suite-wide isolation fixture blocks it.
    """
    from app.llm import PROVIDER_DEFAULTS

    def fake_resolve(preferred_provider=None, explicit_key=None):
        name = (preferred_provider or "groq").lower()
        config = PROVIDER_DEFAULTS.get(name, PROVIDER_DEFAULTS["groq"])
        return name, explicit_key or "test-key", config

    monkeypatch.setattr("app.llm.resolve_provider", fake_resolve)
    monkeypatch.setattr("app.workflow.resolve_provider", fake_resolve)

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            content = responder(json or {})
            return FakeResponse(
                {"choices": [{"message": {"content": content}}]}
            )

    monkeypatch.setattr("app.llm.httpx.Client", FakeClient)


def test_model_backed_stages_produce_ranked_ideas(monkeypatch) -> None:
    """With a working model the council must produce ideas, ranks and validation."""
    no_search_results(monkeypatch)

    def responder(payload: dict) -> str:
        prompt = str(payload.get("messages", [{}])[-1].get("content", ""))
        if "customized research plan" in prompt:
            return json.dumps(
                {
                    "complexity": "multi_faceted_research",
                    "rationale": "test",
                    "convening_speech": "Convened.",
                    "objectives": ["o"],
                    "subtasks": [],
                }
            )
        if "brainstormed_ideas" in prompt:
            return json.dumps(
                {
                    "brainstormed_ideas": [
                        {
                            "id": "idea-1",
                            "title": "Transfer the lattice trick",
                            "transferred_domain": "crystallography",
                            "mechanism": "Use a self-healing lattice to absorb strain.",
                            "flaw_addressed": "dendrite growth at the interface",
                            "feasibility_score": 0.6,
                            "experiment_protocol": "Build a 10-cell stack and cycle it 500 times.",
                            "expected_impact": "Slower degradation.",
                        }
                    ],
                    "overcome_strategies": [
                        {
                            "bottleneck": "dendrite growth at the interface",
                            "solution_strategy": "Absorb strain",
                            "primary_mechanism": "self-healing lattice",
                            "expected_gain": "slower degradation",
                        }
                    ],
                }
            )
        if "feasibility" in prompt:
            return json.dumps(
                {
                    "ranked": [
                        {
                            "id": "idea-1",
                            "feasibility": 0.7,
                            "impact": 0.8,
                            "novelty": 0.6,
                            "cost_to_test": 0.3,
                            "why_it_should_work": "Strain is relieved before it nucleates a defect.",
                            "risks": ["may reduce conductivity"],
                            "next_test": "Cycle a 10-cell stack 500 times.",
                        }
                    ]
                }
            )
        return json.dumps({"ok": True, "detail": "x" * 200})

    _install_fake_provider(monkeypatch, responder)

    result = start_run(
        "solid-state electrolytes",
        "How do we stop dendrite growth at the interface?",
        model_provider="groq",
        api_key="test-key",
    )

    ideas = result.get("ranked_ideas") or []
    assert ideas, "the council must rank ideas when a model is available"
    idea = ideas[0]
    assert idea["title"] == "Transfer the lattice trick"
    assert idea["status"] == "shortlisted"
    assert idea["validation_level"] in {"L0", "L1"}
    assert idea["next_test"]
    assert idea["risks"]
    assert idea["rank"] == 1

    validation = result.get("validation_results") or []
    assert validation and validation[0]["idea_id"] == "idea-1"

    spend = result.get("spend") or {}
    assert spend.get("calls", 0) > 0
    assert spend.get("usd", 0) > 0


def test_failed_model_calls_are_not_charged(monkeypatch) -> None:
    """A call that returns nothing costs the provider nothing, so it costs nothing."""
    no_search_results(monkeypatch)
    _install_fake_provider(monkeypatch, lambda payload: "")

    result = start_run(
        "battery storage",
        "What changed in grid-scale battery storage?",
        model_provider="groq",
        api_key="test-key",
    )

    spend = result.get("spend") or {}
    assert spend.get("usd", 0) == 0.0
    assert spend.get("calls", 0) == 0
    assert result.get("provider_failures"), "the failure must be recorded"


def test_auto_mode_runs_the_intake_classifier(monkeypatch) -> None:
    """FR-IN-1: with no explicit mode the classifier must decide."""
    no_search_results(monkeypatch)

    def fake_role(state: object, agent: str, prompt: str, *args: object, **kwargs: object):
        if "Classify this research request" in prompt:
            return {
                "mode": "topic",
                "confidence": 0.9,
                "reasoning": "The input names a field, not a failure.",
                "topic": "battery storage",
            }
        return None

    monkeypatch.setattr("app.workflow.call_role_llm_json", fake_role)
    monkeypatch.setattr("app.workflow.call_llm_json", lambda *a, **k: None)
    monkeypatch.setattr("app.discovery.search_web", lambda *a, **k: [])

    result = start_run("battery storage", "Tell me about battery storage", mode="auto")

    assert result.get("intake", {}).get("mode") == "topic"
    assert result.get("mode") == "topic"
    events = [event["event"] for event in result.get("audit", [])]
    assert "intake_classified" in events
    assert "mode_selected" in events


def test_explicit_problem_mode_skips_the_classifier(monkeypatch) -> None:
    """An explicit mode must not be overridden by the classifier."""
    no_search_results(monkeypatch)
    called: list[str] = []

    def fake_json(prompt: str, *args: object, **kwargs: object) -> dict[str, object] | None:
        called.append(prompt)
        return None

    monkeypatch.setattr("app.workflow.call_llm_json", fake_json)
    monkeypatch.setattr("app.workflow.call_role_llm_json", fake_json)

    result = start_run(
        "battery storage",
        "What changed in grid-scale battery storage?",
        mode="problem",
    )

    assert result.get("mode") == "problem"
    assert not any("Classify this research request" in prompt for prompt in called)


def test_council_stages_charge_the_run_budget(monkeypatch) -> None:
    """Every model call the council makes must be charged to the budget.

    The council stages used the `_llm` path, which did not record spend, so
    the budget meter stayed at zero while the run was clearly calling models.
    """
    no_search_results(monkeypatch)

    def fake_json(prompt: str, *args: object, **kwargs: object) -> dict[str, object] | None:
        return {"ok": True, "detail": "y" * 200}

    monkeypatch.setattr("app.workflow.call_llm_json", fake_json)
    monkeypatch.setattr("app.workflow.call_role_llm_json", fake_json)

    result = start_run(
        "battery storage",
        "What changed in grid-scale battery storage?",
        model_provider="groq",
        api_key="test-key",
    )

    spend = result.get("spend") or {}
    assert spend.get("calls", 0) > 1, "the council makes several model calls"
    assert spend.get("usd", 0) > 0
    assert spend.get("tokens", 0) > 0
