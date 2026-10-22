"""Central configuration for ForesightForge.

Every tunable limit lives here and is driven by environment variables so that
deployments can adjust behaviour without editing source code. Defaults mirror
the values that were previously hardcoded in the search, workflow and API layers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SearchConfig:
    """Bounds for public web search and page retrieval."""

    max_queries: int = field(default_factory=lambda: _env_int("MAX_QUERIES", 3))
    results_per_query: int = field(default_factory=lambda: _env_int("RESULTS_PER_QUERY", 5))
    max_sources: int = field(default_factory=lambda: _env_int("MAX_SOURCES", 6))
    search_timeout_seconds: float = field(default_factory=lambda: _env_float("SEARCH_TIMEOUT_SECONDS", 12.0))
    fetch_timeout_seconds: float = field(default_factory=lambda: _env_float("FETCH_TIMEOUT_SECONDS", 8.0))
    max_redirects: int = field(default_factory=lambda: _env_int("MAX_REDIRECTS", 3))
    max_page_bytes: int = field(default_factory=lambda: _env_int("MAX_PAGE_BYTES", 1_500_000))
    max_content_chars: int = field(default_factory=lambda: _env_int("MAX_CONTENT_CHARS", 12_000))
    max_fetch_workers: int = field(default_factory=lambda: _env_int("MAX_FETCH_WORKERS", 3))
    search_retries: int = field(default_factory=lambda: _env_int("SEARCH_RETRIES", 3))
    search_retry_delay_seconds: float = field(
        default_factory=lambda: _env_float("SEARCH_RETRY_DELAY_SECONDS", 3.0)
    )
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "SEARCH_USER_AGENT", "ForesightForge/0.1 (evidence research source retrieval)"
        )
    )


@dataclass(frozen=True)
class WorkflowConfig:
    """Bounds for the autonomous R&D workflow."""

    max_rounds: int = field(default_factory=lambda: _env_int("MAX_WORKFLOW_ROUNDS", 2))
    # The council makes one model call per stage plus one per research subagent,
    # so the default budget must cover plan+deconstruct+gather(N)+attack+
    # cross_examine+refine+project+synthesize+cite(M)+verify.
    max_tool_calls: int = field(default_factory=lambda: _env_int("MAX_TOOL_CALLS", 24))
    run_timeout_seconds: float = field(default_factory=lambda: _env_float("RUN_TIMEOUT_SECONDS", 900.0))
    max_subagents: int = field(default_factory=lambda: _env_int("MAX_SUBAGENTS", 3))
    max_attempts: int = field(default_factory=lambda: _env_int("MAX_ATTEMPTS", 2))
    convergence_threshold: float = field(default_factory=lambda: _env_float("CONVERGENCE_THRESHOLD", 0.85))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.2))
    # A stage that returns a large structured document (the research plan, the
    # idea board) needs room. When a provider truncates the response the call
    # is retried with twice the budget, up to `llm_max_token_retries` times.
    llm_max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 8192))
    llm_max_token_retries: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKEN_RETRIES", 3))
    # Hard ceiling on the retry budget so a pathological prompt cannot ask the
    # provider for an unbounded response.
    llm_max_tokens_ceiling: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS_CEILING", 131072))
    # A local or self-hosted model can take a minute or more per call when it
    # is reasoning through a long structured response. The default is sized
    # for that, not for a fast hosted API.
    llm_timeout_seconds: float = field(default_factory=lambda: _env_float("LLM_TIMEOUT_SECONDS", 300.0))
    context_chars: int = field(default_factory=lambda: _env_int("CONTEXT_CHARS", 12_000))

    @property
    def recursion_limit(self) -> int:
        """LangGraph recursion budget derived from the configured round count."""
        return 2 * self.max_rounds + 12


@dataclass(frozen=True)
class DiscoveryConfig:
    """Bounds for the Topic Discovery subgraph (PRD stages D1 to D6)."""

    enabled: bool = field(default_factory=lambda: _env_bool("DISCOVERY_ENABLED", True))
    max_panel_rounds: int = field(default_factory=lambda: _env_int("MAX_PANEL_ROUNDS", 3))
    max_pain_points: int = field(default_factory=lambda: _env_int("MAX_PAIN_POINTS", 24))
    max_problem_candidates: int = field(default_factory=lambda: _env_int("MAX_PROBLEM_CANDIDATES", 8))
    max_subtopics: int = field(default_factory=lambda: _env_int("MAX_SUBTOPICS", 7))
    convergence_threshold: float = field(
        default_factory=lambda: _env_float("PANEL_CONVERGENCE_THRESHOLD", 0.8)
    )
    min_evidence_per_problem: int = field(default_factory=lambda: _env_int("MIN_EVIDENCE_PER_PROBLEM", 1))
    auto_select_top_n: int = field(default_factory=lambda: _env_int("AUTO_SELECT_TOP_N", 1))


@dataclass(frozen=True)
class BudgetConfig:
    """Per-run spend limits (PRD non-functional: cost control)."""

    default_max_usd: float = field(default_factory=lambda: _env_float("DEFAULT_MAX_USD", 5.0))
    max_usd_ceiling: float = field(default_factory=lambda: _env_float("MAX_USD_CEILING", 50.0))
    default_depth: str = field(default_factory=lambda: os.getenv("DEFAULT_DEPTH", "standard"))
    depth_max_rounds: dict[str, int] = field(
        default_factory=lambda: {
            "quick": _env_int("DEPTH_QUICK_ROUNDS", 1),
            "standard": _env_int("DEPTH_STANDARD_ROUNDS", 2),
            "deep": _env_int("DEPTH_DEEP_ROUNDS", 4),
        }
    )
    depth_max_queries: dict[str, int] = field(
        default_factory=lambda: {
            "quick": _env_int("DEPTH_QUICK_QUERIES", 2),
            "standard": _env_int("DEPTH_STANDARD_QUERIES", 3),
            "deep": _env_int("DEPTH_DEEP_QUERIES", 5),
        }
    )
    depth_max_sources: dict[str, int] = field(
        default_factory=lambda: {
            "quick": _env_int("DEPTH_QUICK_SOURCES", 4),
            "standard": _env_int("DEPTH_STANDARD_SOURCES", 6),
            "deep": _env_int("DEPTH_DEEP_SOURCES", 10),
        }
    )


@dataclass(frozen=True)
class AppConfig:
    """Top level application configuration."""

    search: SearchConfig = field(default_factory=SearchConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    )
    require_citation: bool = field(default_factory=lambda: _env_bool("REQUIRE_CITATION", True))
    require_human_checkpoint: bool = field(
        default_factory=lambda: _env_bool("REQUIRE_HUMAN_CHECKPOINT", False)
    )


settings = AppConfig()
