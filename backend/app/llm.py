import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("foresightforge.llm")

# Sentinel returned when a provider truncated the response because the token
# budget was too small. It is distinct from a genuine failure so the caller
# can retry with a larger budget instead of giving up.
_TRUNCATED = "__truncated__"

# Provider Registry & Defaults
PROVIDER_DEFAULTS = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "meta/llama-3.3-70b-instruct",
        "env_keys": ["NVIDIA_API_KEY", "NIM_API_KEY", "MODEL_API_KEY"],
        "api_type": "openai",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_keys": ["OPENAI_API_KEY", "MODEL_API_KEY"],
        "api_type": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
        "env_keys": ["ANTHROPIC_API_KEY", "MODEL_API_KEY"],
        "api_type": "anthropic",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "MODEL_API_KEY"],
        "api_type": "openai",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_keys": ["GROQ_API_KEY", "MODEL_API_KEY"],
        "api_type": "openai",
    },
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "default_model": "llama3.1",
        "env_keys": ["OLLAMA_API_KEY", "MODEL_API_KEY"],
        "api_type": "openai",
    },
    "custom": {
        "base_url": os.getenv("MODEL_BASE_URL", "http://localhost:8000/v1"),
        "default_model": os.getenv("MODEL_NAME", "default"),
        "env_keys": ["MODEL_API_KEY"],
        "api_type": "openai",
    },
}


def resolve_provider(
    preferred_provider: str | None = None,
    explicit_key: str | None = None,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    """Resolves active LLM provider, API key, and configuration.
    Defaults to 'nvidia' if NVIDIA_API_KEY or NIM_API_KEY is detected,
    or checks explicit / environment settings.
    """
    provider_name = (
        preferred_provider
        or os.getenv("LLM_PROVIDER")
        or os.getenv("MODEL_PROVIDER")
    )

    if provider_name:
        provider_name = provider_name.strip().lower()
        if provider_name in PROVIDER_DEFAULTS:
            config = PROVIDER_DEFAULTS[provider_name]
            key = explicit_key
            if not key:
                for k in config["env_keys"]:
                    val = os.getenv(k)
                    if val:
                        key = val.strip()
                        break
            if key or provider_name == "ollama":
                return provider_name, key or "ollama-local", config

    # Auto-detect available keys in priority order: NVIDIA NIM -> Anthropic -> Gemini -> Groq -> OpenAI -> Ollama
    auto_detect_order = ["nvidia", "anthropic", "gemini", "groq", "openai", "custom"]
    for prov in auto_detect_order:
        cfg = PROVIDER_DEFAULTS[prov]
        for env_k in cfg["env_keys"]:
            val = os.getenv(env_k)
            if val and val.strip():
                return prov, val.strip(), cfg

    # Check if local Ollama base URL is reachable or specified
    if os.getenv("OLLAMA_BASE_URL"):
        return "ollama", "ollama-local", PROVIDER_DEFAULTS["ollama"]

    return None, None, None


def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    timeout_seconds: float | None = None,
) -> str | None:
    """Dispatches a prompt to the resolved LLM provider.

    Returns the raw completion string, or None when the provider fails. A
    response that was cut short by the token budget is reported as a failure
    rather than returned as empty text, because an empty string parses as
    nothing and would silently disable the stage.
    """
    resolved_provider, resolved_key, config = resolve_provider(provider, api_key)
    if not resolved_provider or not config:
        return None

    from .config import settings

    if max_tokens is None:
        max_tokens = settings.workflow.llm_max_tokens
    if timeout_seconds is None:
        timeout_seconds = settings.workflow.llm_timeout_seconds

    target_model = (
        model
        or os.getenv("MODEL_NAME")
        or config["default_model"]
    )
    base_url = (
        os.getenv("MODEL_BASE_URL")
        or config["base_url"]
    ).rstrip("/")

    try:
        if config["api_type"] == "anthropic":
            headers = {
                "x-api-key": resolved_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            messages = [{"role": "user", "content": prompt}]
            payload: dict[str, Any] = {
                "model": target_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                payload["system"] = system_prompt

            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(f"{base_url}/messages", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                stop_reason = data.get("stop_reason")
                content = data.get("content", [])
                text = ""
                if content and isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text":
                            text = block.get("text") or ""
                            break
                if stop_reason == "max_tokens" or not text.strip():
                    logger.warning(
                        "LLM call to '%s' (model: %s) was cut short (stop_reason=%s). "
                        "Retrying with a larger token budget.",
                        resolved_provider, target_model, stop_reason,
                    )
                    return _TRUNCATED
                return text

        else:
            # Standard OpenAI-Compatible Endpoint (NVIDIA NIM, Groq, Gemini, OpenAI, Ollama)
            headers = {
                "Content-Type": "application/json",
            }
            if resolved_key and resolved_key != "ollama-local":
                headers["Authorization"] = f"Bearer {resolved_key}"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            endpoint = f"{base_url}/chat/completions"
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    choice = choices[0]
                    finish_reason = choice.get("finish_reason")
                    message = choice.get("message", {}) or {}
                    content = message.get("content") or ""
                    if finish_reason == "length" or not content.strip():
                        logger.warning(
                            "LLM call to '%s' (model: %s) was cut short (finish_reason=%s, %d chars). "
                            "Retrying with a larger token budget.",
                            resolved_provider, target_model, finish_reason, len(content),
                        )
                        return _TRUNCATED
                    return content
                return None

    except Exception as exc:
        logger.warning(
            "LLM call to '%s' (model: %s) failed: %s. Using first-principles fallback.",
            resolved_provider, target_model, exc
        )
        return None


def call_llm_json(
    prompt: str,
    system_prompt: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> dict[str, Any] | None:
    """Calls the active LLM expecting a structured JSON response.

    If the provider truncated the response because the token budget was too
    small, the call is retried with a larger budget. A truncated response is
    useless: it cannot be parsed and would silently disable the stage.
    """
    from .config import settings

    json_system = (
        (system_prompt or "")
        + "\n\nCRITICAL INSTRUCTION: You must respond ONLY with a valid, parseable JSON object. "
        "Do NOT include markdown backticks like ```json, do not include preamble or conversational text. "
        "Your entire output must start with { and end with }. "
        "Keep the response short: honour any item and length limits in the request, "
        "and keep every text field to a few sentences. A response that is cut off "
        "by the token limit is discarded and the task is lost."
    ).strip()

    budget = max_tokens if max_tokens is not None else settings.workflow.llm_max_tokens
    raw = call_llm(
        prompt=prompt,
        system_prompt=json_system,
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=budget,
    )

    # The response was cut short. Retry with more room before giving up.
    # The first retry jumps straight to a generous budget, because a model
    # that truncated a long document needs real headroom rather than a
    # marginal increase. Later retries keep doubling.
    retries = 0
    while raw == _TRUNCATED and retries < settings.workflow.llm_max_token_retries:
        retries += 1
        budget = max(budget * 2, 16384) if budget < 16384 else budget * 2
        budget = min(budget, settings.workflow.llm_max_tokens_ceiling)
        logger.info(
            "Retrying the LLM call with max_tokens=%d after a truncated response.", budget
        )
        raw = call_llm(
            prompt=prompt,
            system_prompt=json_system,
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=budget,
        )

    if raw == _TRUNCATED:
        logger.warning("LLM response remained truncated after %d retries.", retries)
        return None
    if not raw:
        return None

    cleaned = raw.strip()
    # Strip markdown code blocks if the model enclosed them
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    # Extract first JSON object bounds if model added extraneous text
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx : end_idx + 1]

    try:
        return json.loads(cleaned)
    except Exception as exc:
        logger.warning("Failed to parse LLM JSON output (%s): %s", exc, raw[:200])
        return None
