# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Intelligent model router — best AVAILABLE model per task (v1.0.0 major ③).

Picks the right model for a task **deterministically, with zero API calls** (R10):
it reads which provider API keys you've set (the env), crosses them with the
capability map (``model_capabilities.yaml``), and returns the highest-scoring
model for the task class. So "write this email" routes to your best available
critical-thinker, while "classify these 500 rows" routes to a cheap, fast one.

You add/update API keys whenever the landscape changes; the router re-resolves on
every call, so a newly-added provider lights up automatically. Unknown models get
sane defaults — nothing breaks when you add a brand-new one.

Entry points: :func:`available_providers`, :func:`route`, :func:`route_detailed`,
:func:`explain`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_TASK_CLASS = "judgment"

# provider -> the env vars whose presence means "this provider is available".
# Add a row when you start using a new provider (mirror the names in .env.example).
_PROVIDER_ENV: dict[str, list[str]] = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "qwen": ["QWEN_API_KEY", "DASHSCOPE_API_KEY"],
    "glm": ["GLM_API_KEY", "ZAI_API_KEY"],
    "kimi": ["KIMI_API_KEY", "KIMI_CN_API_KEY", "MOONSHOT_API_KEY"],
    "minimax": ["MINIMAX_API_KEY", "MINIMAX_CN_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "novita": ["NOVITA_API_KEY"],
    "nvidia": ["NVIDIA_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "ollama": ["OLLAMA_API_KEY", "OLLAMA_HOST"],
}


@dataclass
class ModelChoice:
    """The router's resolved pick for a task (and why)."""

    model: str
    provider: str
    score: float
    task_class: str
    reason: str


def available_providers(env: dict | None = None) -> set[str]:
    """The set of providers whose API key is present in ``env`` (defaults to os.environ)."""
    e = env if env is not None else os.environ
    return {p for p, keys in _PROVIDER_ENV.items() if any(e.get(k) for k in keys)}


def packaged_capabilities_path() -> Path:
    return Path(__file__).resolve().parent / "model_capabilities.yaml"


def load_capabilities(path: str | Path | None = None) -> dict:
    """Load the capability map (defaults to the packaged ``model_capabilities.yaml``)."""
    p = Path(path) if path is not None else packaged_capabilities_path()
    if not p.exists():
        return {"task_classes": {}, "models": []}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {"task_classes": {}, "models": []}
    return data or {"task_classes": {}, "models": []}


def _score(model: dict, spec: dict) -> float:
    tier = float(model.get("reasoning_tier", 2)) / 5.0
    cost = float(model.get("cost_tier", 3)) / 5.0
    strengths = set(model.get("strengths", []))
    want = set(spec.get("strengths", []))
    bonus = 0.3 * len(strengths & want)
    return float(spec.get("reasoning", 0.5)) * tier + bonus - float(spec.get("cost", 0.0)) * cost


def route_detailed(
    task_class: str = DEFAULT_TASK_CLASS,
    *,
    env: dict | None = None,
    capabilities: dict | None = None,
) -> ModelChoice | None:
    """Resolve the best available model for ``task_class``. Deterministic, zero-LLM.

    Returns ``None`` only when no configured provider has a key set.
    """
    caps = capabilities if capabilities is not None else load_capabilities()
    classes = caps.get("task_classes", {})
    spec = classes.get(task_class) or classes.get(DEFAULT_TASK_CLASS) or {
        "reasoning": 1.0,
        "cost": 0.0,
        "strengths": [],
    }
    require = set(spec.get("require", []))
    avail = available_providers(env)

    candidates: list[tuple[dict, float]] = []
    for model in caps.get("models", []):
        if model.get("provider") not in avail:
            continue
        if require and not (require <= set(model.get("strengths", []))):
            continue
        candidates.append((model, _score(model, spec)))

    if not candidates:
        return None

    candidates.sort(key=lambda ms: (-ms[1], str(ms[0].get("id", ""))))
    best, score = candidates[0]
    reason = (
        f"task '{task_class}': top of {len(candidates)} model(s) from available "
        f"provider(s) [{', '.join(sorted(avail))}], ranked by reasoning×strengths−cost"
    )
    return ModelChoice(
        model=str(best.get("id", "")),
        provider=str(best.get("provider", "")),
        score=score,
        task_class=task_class,
        reason=reason,
    )


def route(
    task_class: str = DEFAULT_TASK_CLASS,
    *,
    env: dict | None = None,
    capabilities: dict | None = None,
) -> str | None:
    """The best available model id for ``task_class`` (or ``None`` if no provider is set)."""
    choice = route_detailed(task_class, env=env, capabilities=capabilities)
    return choice.model if choice else None


def explain(
    task_class: str = DEFAULT_TASK_CLASS,
    *,
    env: dict | None = None,
    capabilities: dict | None = None,
) -> str:
    """A human-readable one-liner: which model, and why (for ``xavani model route``)."""
    choice = route_detailed(task_class, env=env, capabilities=capabilities)
    if choice is None:
        return (
            f"No model available for '{task_class}': set a provider API key "
            f"(e.g. ANTHROPIC_API_KEY / OPENAI_API_KEY) and try again."
        )
    return f"{choice.task_class} → {choice.model} ({choice.provider})  ·  {choice.reason}"
