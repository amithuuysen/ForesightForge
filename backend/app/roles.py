"""Agent roster, role tiers and per-role model routing.

The HLD forbids hardcoded model ids: roles resolve to a tier (``fast``,
``reason``, ``creative``, ``critic``) and tiers resolve to a concrete provider
model through ``config/models.yaml``. The critic tier is deliberately allowed to
point at a different vendor than the ideators so the skeptic is not fooled by
the same weights that produced the idea.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_ROLES: dict[str, dict[str, Any]] = {
    "fast": {"model": "", "temperature": 0.2},
    "reason": {"model": "", "temperature": 0.4},
    "creative": {"model": "", "temperature": 0.9},
    "critic": {"model": "", "temperature": 0.2},
}

DEFAULT_AGENTS: dict[str, str] = {
    "skeptic": "critic",
    "novelty_checker": "critic",
    "judge": "critic",
    "ideator": "creative",
    "panel_persona": "creative",
    "landscape_scout": "fast",
    "evidence_grader": "fast",
    "classify_intake": "fast",
}


@dataclass(frozen=True)
class Persona:
    """A speaking agent in the council or the discovery panel."""

    id: str
    initials: str
    name: str
    mandate: str
    color: str
    tier: str = "reason"
    cluster: str = "council"

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "initials": self.initials,
            "name": self.name,
            "mandate": self.mandate,
            "color": self.color,
            "tier": self.tier,
            "cluster": self.cluster,
        }


# --- The standing R&D council (used by the research pipeline) -----------------

COUNCIL_PERSONAS: tuple[Persona, ...] = (
    Persona(
        id="lead",
        initials="PI",
        name="Principal Investigator",
        mandate="Frame the problem, route the council, synthesise the blueprint.",
        color="#5AB0FF",
        tier="reason",
    ),
    Persona(
        id="subagent-1",
        initials="AD",
        name="Architecture & Diagnostics",
        mandate="Reconstruct the base architecture and isolate the bottleneck.",
        color="#4ADE9C",
        tier="reason",
    ),
    Persona(
        id="subagent-2",
        initials="CD",
        name="Cross-Domain Invention",
        mandate="Transfer paradigms from adjacent fields into new mechanisms.",
        color="#F5A524",
        tier="creative",
    ),
    Persona(
        id="subagent-3",
        initials="RT",
        name="Adversarial Red-Team",
        mandate="Attack every claim, find the failure mode, refuse comfort.",
        color="#FF7A70",
        tier="critic",
    ),
    Persona(
        id="citation",
        initials="PA",
        name="Prior Art Auditor",
        mandate="Grade every source and verify citations at passage level.",
        color="#B79CFF",
        tier="fast",
    ),
    Persona(
        id="judge",
        initials="SJ",
        name="Scientific Rigour Judge",
        mandate="Score the work against the rigour rubric and rule on evidence.",
        color="#F472B6",
        tier="critic",
    ),
)

# --- The discovery panel (Topic Discovery mode, FR-DS-4) ---------------------

PANEL_PERSONAS: tuple[Persona, ...] = (
    Persona(
        id="practitioner",
        initials="PR",
        name="Practitioner",
        mandate="Speak from operating reality: what actually breaks, costs and blocks.",
        color="#F5A524",
        tier="creative",
        cluster="panel",
    ),
    Persona(
        id="academic",
        initials="AC",
        name="Academic",
        mandate="Defend the published record and demand reproducible evidence.",
        color="#5AB0FF",
        tier="creative",
        cluster="panel",
    ),
    Persona(
        id="strategist",
        initials="ST",
        name="Strategist",
        mandate="Judge tractability, market pull and what is worth funding.",
        color="#4ADE9C",
        tier="reason",
        cluster="panel",
    ),
    Persona(
        id="contrarian",
        initials="CO",
        name="Contrarian",
        mandate="Challenge consensus, hunt for overstated risk and false problems.",
        color="#FF7A70",
        tier="critic",
        cluster="panel",
    ),
    Persona(
        id="futurist",
        initials="FU",
        name="Futurist",
        mandate="Surface emerging technologies and second-order consequences.",
        color="#B79CFF",
        tier="creative",
        cluster="panel",
    ),
)

MODERATOR = Persona(
    id="moderator",
    initials="MO",
    name="Moderator",
    mandate="Force convergence, summarise the round and name what stays unresolved.",
    color="#4ADE9C",
    tier="reason",
    cluster="panel",
)

ALL_PERSONAS: tuple[Persona, ...] = COUNCIL_PERSONAS + PANEL_PERSONAS + (MODERATOR,)

PERSONA_BY_ID: dict[str, Persona] = {persona.id: persona for persona in ALL_PERSONAS}


def _config_path() -> Path:
    override = os.getenv("MODELS_CONFIG_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / "config" / "models.yaml"


def load_models_config() -> dict[str, Any]:
    """Read ``config/models.yaml`` with safe fallbacks when the file is absent."""
    path = _config_path()
    if not path.exists():
        return {"roles": dict(DEFAULT_ROLES), "agents": dict(DEFAULT_AGENTS)}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {"roles": dict(DEFAULT_ROLES), "agents": dict(DEFAULT_AGENTS)}
    roles = {**DEFAULT_ROLES, **(raw.get("roles") or {})}
    agents = {**DEFAULT_AGENTS, **(raw.get("agents") or {})}
    return {"roles": roles, "agents": agents}


def resolve_role(agent: str) -> str:
    """Map an agent name to its model tier."""
    config = load_models_config()
    return str(config["agents"].get(agent, "reason"))


def resolve_model(agent: str) -> dict[str, Any]:
    """Resolve the provider/model and temperature an agent should use."""
    config = load_models_config()
    tier = resolve_role(agent)
    spec = config["roles"].get(tier) or DEFAULT_ROLES["reason"]
    return {
        "tier": tier,
        "model": str(spec.get("model") or ""),
        "temperature": float(spec.get("temperature", 0.2)),
    }


def persona(persona_id: str) -> Persona:
    return PERSONA_BY_ID.get(persona_id, MODERATOR)


# --- Cost estimation --------------------------------------------------------

# Rough blended price per 1M tokens in USD, used only to show the user a
# running cost figure. The authoritative number would come from a provider
# pricing API; this keeps the budget meter honest without inventing precision.
_COST_PER_MILLION: dict[str, tuple[float, float]] = {
    "nvidia": (0.20, 0.60),
    "openai": (0.15, 0.60),
    "anthropic": (3.00, 15.00),
    "gemini": (0.10, 0.40),
    "groq": (0.05, 0.08),
    "ollama": (0.0, 0.0),
    "custom": (0.0, 0.0),
}


def estimate_cost_usd(provider: str | None, prompt_chars: int, completion_chars: int) -> tuple[float, int]:
    """Estimate spend and token count for one model call.

    Returns ``(usd, tokens)``. Tokens are approximated as ``chars / 4`` which is
    close enough for a budget meter and is never used for billing.
    """
    prompt_tokens = max(1, prompt_chars // 4) if prompt_chars else 0
    completion_tokens = max(1, completion_chars // 4) if completion_chars else 0
    tokens = prompt_tokens + completion_tokens
    input_price, output_price = _COST_PER_MILLION.get((provider or "").lower(), (0.30, 1.20))
    usd = (prompt_tokens / 1_000_000) * input_price + (completion_tokens / 1_000_000) * output_price
    return round(usd, 6), tokens
