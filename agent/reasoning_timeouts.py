# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B01: per-model-family max reasoning tokens.

Reasoning models burn tokens in their thinking phase.  This small
database pins a sane ceiling per model family so a single runaway turn
cannot blow the budget.  Lookup is substring-based and longest-match
wins, so ``claude-3-5-haiku`` is matched before the generic
``claude`` entry.  A model with no entry gets no cap (``0``), matching
today's behavior.
"""

from __future__ import annotations

# Family substring -> max reasoning tokens.  Keep entries coarse:
# one row per pricing/thinking tier, not per model id.
MAX_REASONING_TOKENS_BY_FAMILY: dict[str, int] = {
    "claude-3-5-haiku": 8192,
    "claude-3-5-sonnet": 16000,
    "claude-3-7-sonnet": 32000,
    "claude-sonnet-4": 32000,
    "claude-opus-4": 48000,
    "gpt-5-mini": 8192,
    "gpt-5": 32000,
    "grok-3-mini": 16000,
    "grok-4-fast": 16000,
    "grok-4": 32000,
    "gemini": 32000,
    "deepseek-reasoner": 16000,
    "kimi": 16000,
    "qwen3": 16000,
    "glm": 16000,
}

# Longest matching family key wins.
_FAMILY_KEYS: tuple[str, ...] = tuple(
    sorted(MAX_REASONING_TOKENS_BY_FAMILY, key=len, reverse=True)
)


def max_reasoning_tokens_for(model: str | None, fallback: int = 0) -> int:
    """Return the reasoning-token ceiling for ``model``, or ``fallback``.

    ``0`` (the default fallback) means "no cap" — callers that already
    enforce a budget keep their behavior for unknown families.
    """
    if not model:
        return fallback
    lowered = model.lower()
    for family in _FAMILY_KEYS:
        if family in lowered:
            return MAX_REASONING_TOKENS_BY_FAMILY[family]
    return fallback
