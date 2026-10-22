"""Shared test fixtures.

The most important job here is isolation: the test suite must never reach a
live model provider. A developer with ``LLM_PROVIDER`` set in their shell or
a ``.env`` file would otherwise get tests that make real network calls, take
minutes, and assert on whatever the provider happened to return.

Every test therefore runs with provider credentials stripped, and the
provider resolution is blocked outright. A test that needs a model mocks the
HTTP boundary instead (see ``test_workflow.py``).
"""

from __future__ import annotations

import pytest


_PROVIDER_ENV_VARS = (
    "LLM_PROVIDER",
    "MODEL_PROVIDER",
    "MODEL_NAME",
    "MODEL_BASE_URL",
    "MODEL_API_KEY",
    "NVIDIA_API_KEY",
    "NIM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "OLLAMA_BASE_URL",
    "OLLAMA_API_KEY",
)


@pytest.fixture(autouse=True)
def _no_live_provider(monkeypatch) -> None:
    """Strip every provider credential and block provider resolution."""
    for name in _PROVIDER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    # Block resolution outright so no test can accidentally call out.
    monkeypatch.setattr("app.llm.resolve_provider", lambda *args, **kwargs: (None, None, None))
