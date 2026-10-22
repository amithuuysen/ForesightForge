import json
import pytest
from app.llm import resolve_provider, call_llm, call_llm_json, PROVIDER_DEFAULTS


def test_resolve_provider_nvidia_default(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-12345")
    provider, key, config = resolve_provider()
    assert provider == "nvidia"
    assert key == "nvapi-test-key-12345"
    assert config["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert "llama" in config["default_model"].lower()


def test_resolve_provider_explicit_openai(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    provider, key, config = resolve_provider("openai")
    assert provider == "openai"
    assert key == "sk-test-key"
    assert "api.openai.com" in config["base_url"]


def test_resolve_provider_anthropic(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    provider, key, config = resolve_provider()
    assert provider == "anthropic"
    assert key == "sk-ant-test"
    assert config["api_type"] == "anthropic"


def test_resolve_provider_groq(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    provider, key, config = resolve_provider()
    assert provider == "groq"
    assert key == "gsk-test"
    assert "groq.com" in config["base_url"]


def test_resolve_provider_gemini(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    provider, key, config = resolve_provider()
    assert provider == "gemini"
    assert key == "gemini-test-key"


def test_resolve_provider_ollama(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    provider, key, config = resolve_provider()
    assert provider == "ollama"
    assert "11434" in config["base_url"]


def test_resolve_provider_none(monkeypatch):
    for prov in PROVIDER_DEFAULTS:
        for k in PROVIDER_DEFAULTS[prov]["env_keys"]:
            monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    provider, key, config = resolve_provider()
    assert provider is None
    assert key is None


def test_call_llm_without_key_returns_none(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    res = call_llm("Explain attention")
    assert res is None


def test_call_llm_json_strips_markdown_code_fences(monkeypatch):
    # Mock call_llm to simulate a model returning ```json { "hello": "world" } ```
    monkeypatch.setattr(
        "app.llm.call_llm",
        lambda *args, **kwargs: "```json\n{\n  \"status\": \"ok\",\n  \"score\": 95\n}\n```"
    )
    result = call_llm_json("Return status")
    assert result is not None
    assert result["status"] == "ok"
    assert result["score"] == 95


def test_autonomous_workflow_with_active_llm(monkeypatch):
    from app.workflow import start_run

    def mock_call_llm_json(prompt, *args, **kwargs):
        p = prompt.lower()
        if "formulate a customized research plan" in p or "complexity" in p and "subtasks" in p:
            return {
                "complexity": "multi_faceted_research",
                "rationale": "Autonomous PI dynamic rationale for deep exploration.",
                "subagent_count": 3,
                "tool_budget_per_agent": 12,
                "convening_speech": "Autonomous PI live convening address.",
                "objectives": ["Dynamically deconstruct flaw", "Cross-examine failure mode", "Synthesize novel blueprint"],
                "subtasks": [
                    {
                        "subagent_id": "subagent-1",
                        "role": "Autonomous Diagnostics Fellow",
                        "focus": "Diagnostic sweep of quantum noise boundaries",
                        "boundaries": "Quantum limits",
                        "search_strategy": "start_broad_then_narrow",
                        "broad_query": "Quantum coherence loss decoherence times",
                        "narrow_query_templates": ["Quantum dephasing T2 time mitigation"],
                    },
                    {
                        "subagent_id": "subagent-2",
                        "role": "Autonomous Transfer Fellow",
                        "focus": "Topological braid transfer",
                        "boundaries": "Material physics",
                        "search_strategy": "start_broad_then_narrow",
                        "broad_query": "Topological Majorana zero modes braid",
                        "narrow_query_templates": ["Majorana nanowire surface code"],
                    },
                ],
            }
        elif "first-principles base core architecture" in p:
            return {
                "system_name": "Autonomous Quantum Superconducting Qubit Resonator",
                "domain": "Quantum Computing",
                "foundational_summary": "Josephson junction transmon qubit coupled to a readout microwave coplanar waveguide resonator.",
                "governing_equation": "H = 4 E_C (n - n_g)^2 - E_J cos(phi)",
                "primitives": [
                    {
                        "name": "Josephson Tunnel Junction",
                        "category": "Non-Linear Inductance Core",
                        "mechanism": "Cooper pair tunneling through sub-nanometer aluminum oxide barrier.",
                        "role_in_system": "Provides anharmonicity to isolate computational basis states |0> and |1>.",
                        "bottleneck_equation_or_limit": "Dielectric two-level system (TLS) surface loss at metal-substrate interfaces.",
                    },
                    {
                        "name": "Coplanar Waveguide Resonator",
                        "category": "Dispersive Readout Cavity",
                        "mechanism": "Distributed LC transmission line resonant with microwave frequency omega_r.",
                        "role_in_system": "Performs quantum non-demolition dispersive state readout.",
                        "bottleneck_equation_or_limit": "Purcell decay rate gamma_p = (g / Delta)^2 kappa.",
                    },
                    {
                        "name": "Superconducting Ground Plane",
                        "category": "Electromagnetic Shielding",
                        "mechanism": "Niobium or tantalum thin-film screening stray magnetic flux vortices.",
                        "role_in_system": "Protects against non-equilibrium quasiparticle poison.",
                        "bottleneck_equation_or_limit": "Abrikosov vortex pinning failure under ambient magnetic fields.",
                    },
                ],
                "flaw_hotspot": "Interfacial Two-Level System (TLS) Dielectric Loss causing irreversible T1 energy relaxation.",
                "diagnostic_speech": "Autonomous Diagnostics: TLS dielectric loss at interfaces dominates decoherence.",
            }
        elif "adversarial stress-test attack" in p:
            return {
                "speech": "Autonomous Red-Team: TLS defects inside amorphous oxide barriers cause catastrophic phase dephasing under high microwave drive.",
                "critical_vulnerability": "Dielectric TLS saturation ceiling.",
            }
        elif "cross-examination" in p:
            return {
                "turns": [
                    {"speaker_id": "subagent-3", "speaker_name": "Adversarial Red-Team", "speech": "Autonomous Turn 1: High photon flux saturates dielectric TLS, collapsing coherence."},
                    {"speaker_id": "subagent-2", "speaker_name": "Cross-Domain Invention Fellow", "speech": "Autonomous Turn 2: Transferring surface passivation from extreme-UV photolithography eliminates amorphous oxide entirely."},
                    {"speaker_id": "subagent-1", "speaker_name": "Autonomous Diagnostics Fellow", "speech": "Autonomous Turn 3: Measured interface loss tangent drops by 94% under atomic cleanroom passivation."},
                    {"speaker_id": "lead", "speaker_name": "Principal Investigator", "speech": "Autonomous Turn 4: The council has resolved the primary contention. Authorizing Attempt 2."},
                ],
                "disagreements": [
                    {
                        "id": "disagree-1",
                        "speaker_a": "Adversarial Red-Team",
                        "role_a": "Stress-Testing",
                        "stance_a": "Amorphous oxide interface suffers dielectric TLS loss.",
                        "speaker_b": "Cross-Domain Invention Fellow",
                        "role_b": "Invention Transfer",
                        "stance_b": "Extreme-UV lithography surface passivation eliminates oxide.",
                    },
                    {
                        "id": "disagree-2",
                        "speaker_a": "Autonomous Diagnostics Fellow",
                        "role_a": "Diagnostics",
                        "stance_a": "Loss tangent threshold must be under 1e-7.",
                        "speaker_b": "Adversarial Red-Team",
                        "role_b": "Stress-Testing",
                        "stance_b": "Verification requires cryogenic mK dilution refrigerator validation.",
                    },
                ],
            }
        elif "attempt 2 to resolve contested points" in p:
            return {
                "attempt_focus": "Autonomous Re-investigation of cryogenic TLS loss tangents",
                "convergence_score": 0.94,
                "pi_speech": "PI: Attempt 2 verified passivated interfaces.",
                "red_team_speech": "Red-Team: Empirical loss tangent below 1e-7 conceded.",
            }
        elif "quantitative trajectory" in p:
            return {
                "metric_name": "Qubit Coherence Time T1 (microseconds)",
                "projections": [
                    {"year": 2024, "target_metric": 80.0, "baseline_metric": 30.0, "alt_metric": 10.0},
                    {"year": 2027, "target_metric": 240.0, "baseline_metric": 50.0, "alt_metric": 20.0},
                    {"year": 2030, "target_metric": 800.0, "baseline_metric": 70.0, "alt_metric": 30.0},
                    {"year": 2035, "target_metric": 2500.0, "baseline_metric": 90.0, "alt_metric": 40.0},
                ],
            }
        elif "scientific rigour judge" in p:
            return {
                "factual_accuracy": 0.95,
                "citation_accuracy": 0.92,
                "completeness": 0.90,
                "source_quality": 0.93,
                "tool_efficiency": 0.88,
                "overall_score": 0.92,
                "verdict": "PASS",
                "evaluator_notes": "Autonomous Judge: Outstanding first-principles deconstruction and passivated interface resolution.",
            }
        return None

    monkeypatch.setattr("app.workflow.call_llm_json", mock_call_llm_json)
    monkeypatch.setattr("app.workflow.search_web", lambda *args, **kwargs: [
        {"id": "src-q1", "url": "https://quantum.org", "title": "Quantum Coherence", "excerpt": "Josephson junction TLS loss."}
    ])

    events = []
    run_state = start_run(
        domain="Quantum Qubits",
        question="How to overcome TLS loss at transmon interfaces?",
        progress_callback=lambda e: events.append(e),
        model_provider="nvidia",
        model_name="meta/llama-3.3-70b-instruct",
        api_key="nvapi-mock-autonomous-key",
    )

    # Verify that autonomous LLM values propagated through the council
    assert "Autonomous Quantum Superconducting Qubit Resonator" == run_state["core_architecture"]["system_name"]
    assert "Josephson Tunnel Junction" in [p["name"] for p in run_state["core_architecture"]["primitives"]]
    assert any("Autonomous Turn 1" in e.get("speech", "") for e in events)
    assert any("Autonomous Turn 2" in e.get("speech", "") for e in events)
    assert run_state["attempt_history"][-1]["focus"] == "Autonomous Re-investigation of cryogenic TLS loss tangents"
    assert run_state["evaluation"]["overall_score"] == 0.92
    assert "Qubit Coherence Time" in str(events)


def test_truncated_response_is_not_returned_as_empty(monkeypatch):
    """A response cut off by the token budget must not look like an empty answer.

    An empty string parses to nothing and would silently disable the stage
    that asked for it. The caller must see a failure and retry with a larger
    budget.
    """
    calls: list[dict] = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": ""},
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            calls.append(json or {})
            return FakeResponse()

    monkeypatch.setattr("app.llm.httpx.Client", FakeClient)
    monkeypatch.setattr(
        "app.llm.resolve_provider",
        lambda *a, **k: ("groq", "k", {"base_url": "http://x", "default_model": "m", "api_type": "openai", "env_keys": []}),
    )

    result = call_llm_json("hi")
    assert result is None, "a truncated response must not be returned as data"
    assert len(calls) > 1, "the call must be retried with a larger budget"
    budgets = [call.get("max_tokens") for call in calls]
    assert budgets == sorted(budgets), "the budget must grow on each retry"
    assert budgets[-1] > budgets[0]


def test_complete_response_is_returned(monkeypatch):
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"ok": true}'},
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            return FakeResponse()

    monkeypatch.setattr("app.llm.httpx.Client", FakeClient)
    monkeypatch.setattr(
        "app.llm.resolve_provider",
        lambda *a, **k: ("groq", "k", {"base_url": "http://x", "default_model": "m", "api_type": "openai", "env_keys": []}),
    )

    assert call_llm_json("hi") == {"ok": True}
