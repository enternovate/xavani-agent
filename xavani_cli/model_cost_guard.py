# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C02 — Model cost guard.

Warns before switching to models whose per-million-token input cost exceeds
a threshold (default $20/M input, per the 50-update program). Cheap, pure,
zero-LLM: a simple threshold check on models.dev pricing metadata.

Kept as its own module so the CLI, the gateway, and tests share one rule.
"""

from __future__ import annotations

# Default threshold: $20 USD per 1M input tokens (C02 spec).
DEFAULT_COST_GUARD_PER_M_INPUT = 20.0

# Models whose cost metadata is unknown/zero should NOT trip the guard
# (a 0.0 cost usually means "metadata not published", not "free").
_IGNORED_NON_POSITIVE = (0.0, None)


def model_cost_guard(
    model: str,
    cost_input_per_m: float | None,
    provider: str = "",
    threshold: float = DEFAULT_COST_GUARD_PER_M_INPUT,
) -> str | None:
    """Return a warning string when a model's input cost exceeds the guard.

    Args:
        model: The model id (e.g. "anthropic/claude-opus-4-1").
        cost_input_per_m: USD per 1M input tokens, or None/0.0 when unknown.
        provider: Provider label for the message (optional).
        threshold: Cost ceiling in USD per 1M input tokens.

    Returns:
        A human-readable warning, or None when the model is under the
        threshold (or its cost is unknown).
    """
    if cost_input_per_m in _IGNORED_NON_POSITIVE:
        return None
    if cost_input_per_m < 0:
        return None
    if cost_input_per_m <= threshold:
        return None

    label = f"{provider}/" if provider else ""
    return (
        f"Cost guard: {label}{model} is ${cost_input_per_m:.2f}/M input tokens "
        f"(limit ${threshold:.0f}/M). This is an expensive model — double-check "
        f"before switching."
    )
