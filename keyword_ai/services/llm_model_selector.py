"""
LLM Model Selector with Fallback Chain.

Provides a centralized way to select the best available LLM model with
graceful degradation. Supports both OpenAI (gpt-4o -> gpt-4-turbo -> gpt-4)
and Groq providers.

Usage:
    from keyword_ai.services.llm_model_selector import (
        get_llm_model,
        get_provider_chain,
        log_model_selection,
    )

    model_name = get_llm_model()  # e.g. "gpt-4o"
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


# Preference order (best -> graceful fallback)
OPENAI_MODEL_PRIORITY: List[str] = [
    "gpt-4o",            # Default: GPT-4 Omni (fast, cheap, latest)
    "gpt-4o-mini",       # Cheaper Omni variant
    "gpt-4-turbo",       # Previous flagship
    "gpt-4",             # Legacy flagship
    "gpt-3.5-turbo",     # Final fallback
]

GROQ_MODEL_PRIORITY: List[str] = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]


class ModelNotAvailableError(RuntimeError):
    """Raised when a candidate LLM model cannot be used."""


class NoAvailableModelError(RuntimeError):
    """Raised when every model in the fallback chain is unavailable."""


def _configured_openai_model() -> str:
    """Return the user-configured OpenAI model from settings/env."""
    return getattr(settings, "OPENAI_MODEL", "gpt-4o") or "gpt-4o"


def _configured_groq_model() -> str:
    """Return the user-configured Groq model from settings/env."""
    return getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile"


def get_openai_priority() -> List[str]:
    """Return the OpenAI fallback chain with the configured model on top."""
    configured = _configured_openai_model()
    chain = [configured] + [m for m in OPENAI_MODEL_PRIORITY if m != configured]
    return chain


def get_groq_priority() -> List[str]:
    """Return the Groq fallback chain with the configured model on top."""
    configured = _configured_groq_model()
    chain = [configured] + [m for m in GROQ_MODEL_PRIORITY if m != configured]
    return chain


def get_provider_chain() -> List[Tuple[str, str]]:
    """
    Build a (provider, model) chain ordered by preference.

    Returns:
        List of tuples like [("groq", "llama-3.3-70b-versatile"), ("openai", "gpt-4o"), ...]
    """
    use_groq = bool(getattr(settings, "USE_GROQ", True))
    groq_key = getattr(settings, "GROQ_API_KEY", "")
    openai_key = getattr(settings, "OPENAI_API_KEY", "")

    chain: List[Tuple[str, str]] = []

    if use_groq and groq_key:
        for model in get_groq_priority():
            chain.append(("groq", model))

    if openai_key:
        for model in get_openai_priority():
            chain.append(("openai", model))

    return chain


def get_llm_model(provider: Optional[str] = None) -> str:
    """
    Return the active model name for a given provider.

    Args:
        provider: Optional "openai" or "groq". If None, picks based on settings.

    Returns:
        Model name string.

    Raises:
        NoAvailableModelError: If no model could be selected.
    """
    chain = get_provider_chain()
    if not chain:
        raise NoAvailableModelError(
            "No LLM provider configured. Set GROQ_API_KEY or OPENAI_API_KEY."
        )

    if provider:
        for prov, model in chain:
            if prov == provider:
                return model
        raise NoAvailableModelError(f"Provider '{provider}' is not configured.")

    return chain[0][1]


def log_model_selection() -> None:
    """Log the resolved model preference chain for observability/debug."""
    try:
        chain = get_provider_chain()
        if not chain:
            logger.warning("[LLM] No providers configured (Groq/OpenAI keys missing).")
            return
        pretty = " -> ".join(f"{prov}:{model}" for prov, model in chain)
        logger.info("[LLM] Model fallback chain: %s", pretty)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("[LLM] Could not log model selection: %s", exc)


def get_model_metadata(model: str) -> dict:
    """
    Return cost/perf metadata about a model. Used for logging and analytics.
    """
    metadata = {
        # OpenAI models (approx. as of 2025)
        "gpt-4o": {"provider": "openai", "context": 128_000, "tier": "fast-flagship"},
        "gpt-4o-mini": {"provider": "openai", "context": 128_000, "tier": "cheap"},
        "gpt-4-turbo": {"provider": "openai", "context": 128_000, "tier": "flagship"},
        "gpt-4": {"provider": "openai", "context": 8_192, "tier": "legacy-flagship"},
        "gpt-3.5-turbo": {"provider": "openai", "context": 16_385, "tier": "legacy-cheap"},
        # Groq models
        "llama-3.3-70b-versatile": {"provider": "groq", "context": 128_000, "tier": "flagship"},
        "llama-3.1-70b-versatile": {"provider": "groq", "context": 128_000, "tier": "flagship"},
        "llama-3.1-8b-instant": {"provider": "groq", "context": 128_000, "tier": "fast"},
        "mixtral-8x7b-32768": {"provider": "groq", "context": 32_768, "tier": "balanced"},
    }
    return metadata.get(model, {"provider": "unknown", "context": None, "tier": "unknown"})
