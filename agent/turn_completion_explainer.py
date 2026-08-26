# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Turn-completion explainer.

When a turn ends abnormally — empty content after retries, a truncated
stream, a budget/iteration limit, a guardrail halt — the user otherwise
gets a blank or fragmentary response box. This module derives a single
user-visible explanation from ``_turn_exit_reason`` so the agent never
fails to say anything.
"""

from __future__ import annotations

_enabled_cache: bool | None = None

_ENV_VAR = "XAVANI_TURN_EXPLAINER"
_CONFIG_KEY = "turn_completion_explainer"

# Exit reasons produced by conversation_loop tails that represent an
# abnormal end. "text_response(...)" exits never produce explanations.
_TEXT_RESPONSE_PREFIX = "text_response("


def turn_completion_explainer_enabled() -> bool:
    """Return whether the explainer is on. Memoized per process."""
    global _enabled_cache
    if _enabled_cache is not None:
        return _enabled_cache
    _enabled_cache = _resolve_enabled()
    return _enabled_cache


def _reset_enabled_cache_for_tests() -> None:
    """Reset the memo. Test seam only."""
    global _enabled_cache
    _enabled_cache = None


def _resolve_enabled() -> bool:
    import os

    env = os.environ.get(_ENV_VAR)
    if env is not None:
        return env.strip().lower() not in {"0", "false", "no", "off"}
    try:
        from xavani_cli.config import load_config

        cfg = load_config() or {}
        display = cfg.get("display") if isinstance(cfg, dict) else None
        if isinstance(display, dict) and _CONFIG_KEY in display:
            return bool(display.get(_CONFIG_KEY))
    except Exception:
        pass
    return True


def is_partial_fragment(text: str, exit_reason: str) -> bool:
    """Classify a short punctuation-less response as a truncated partial.

    A real terse answer ("Done.", "No?") keeps its text. The "(empty)"
    sentinel and genuinely empty responses are handled by the empty path,
    not here. Single complete words ("done", "OK", "Yes") are answers,
    not truncations — they never qualify.
    """
    stripped = (text or "").strip()
    if not stripped or stripped == "(empty)":
        return False
    if exit_reason.startswith(_TEXT_RESPONSE_PREFIX):
        return False
    if len(stripped) > 24:
        return False
    if stripped[-1:] in {".", "!", "?", "`", ")"}:
        return False
    # A lone word is a complete reply, not a cut-off sentence.
    if " " not in stripped:
        return False
    return True


# Ordered prefix match: longest/most-specific reasons first.
_EXPLANATIONS = {
    "all_retries_exhausted_no_response": (
        "I could not complete this turn: every retry against the model "
        "failed ({cause}). Check provider status or your API key, then send "
        "your message again."
    ),
    "empty_response_exhausted": (
        "I could not produce a response this turn: the model returned empty "
        "content after repeated retries{cause_clause}. Please resend your "
        "message; if it keeps happening, switch models with /model."
    ),
    "partial_stream_recovery": (
        "The model's stream dropped mid-response, so I stopped early. "
        "Partial output above may be incomplete — ask me to continue."
    ),
    "budget_exhausted": (
        "This turn ended because the token/cost budget ran out before I "
        "could finish. Raise the budget or start a fresh session."
    ),
    "max_iterations_reached": (
        "I hit the tool-call iteration limit ({detail}) this turn. The work "
        "is incomplete — narrow the request or raise max_iterations."
    ),
    "error_near_max_iterations": (
        "An error occurred near the iteration limit, so I stopped ({cause}). "
        "The work may be incomplete."
    ),
    "interrupted_by_user": (
        "You interrupted this turn. Partial output above is incomplete."
    ),
    "interrupted_during_api_call": (
        "The turn was interrupted while waiting on the model. Nothing was "
        "lost — send your message again when ready."
    ),
    "guardrail_halt": (
        "A safety guardrail halted this turn before completion. Review the "
        "last tool activity above for what triggered it."
    ),
}

# Generic fallback keeps unknown future reasons covered.
_GENERIC = (
    "This turn ended unexpectedly ({reason}{cause_clause}) before I could "
    "finish properly. Partial output above may be incomplete."
)


def format_turn_completion_explanation(exit_reason: str, cause: str | None = None) -> str | None:
    """Map an abnormal turn-exit reason to user-facing text.

    Returns None for normal ``text_response(...)`` exits so healthy turns
    stay untouched. Always returns something usable for any other reason.
    """
    if not exit_reason or exit_reason.startswith(_TEXT_RESPONSE_PREFIX):
        return None

    cause_text = (cause or "").strip()
    cause_clause = f" ({cause_text})" if cause_text else ""
    detail = ""

    # Exact match first (covers parameterized reasons via their prefix).
    template = _EXPLANATIONS.get(exit_reason)
    if template is None:
        for prefix, candidate in _EXPLANATIONS.items():
            if exit_reason.startswith(prefix + "("):
                if "(" in exit_reason:
                    detail = exit_reason.rsplit("(", 1)[-1].rstrip(")")
                template = candidate
                break
    if template is None:
        return _GENERIC.format(reason=exit_reason, cause_clause=cause_clause)

    return template.format(
        cause=cause_text or "unknown error",
        cause_clause=cause_clause,
        detail=detail or exit_reason.rsplit("(", 1)[-1].rstrip(")") if "(" in exit_reason else "",
    )
