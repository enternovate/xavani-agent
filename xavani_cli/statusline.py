# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C15: statusline API.

Builds the TUI status bar segments from agent state in one place:

- model name + provider
- context usage (tokens used / budget, percentage, color tier)
- turn counter / background task count
- session id (short)

The TUI renders the returned list; this module owns the CONTENT and the
semantics (tier thresholds, format). Deterministic and testable without
a terminal.

Usage::

    from xavani_cli.statusline import build_statusline_segments

    segments = build_statusline_segments(state=agent_state_dict)
    for text, color, bold in segments:
        ...
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# A segment is (text, color_tier, bold). color_tier is one of
# "default" | "good" | "warn" | "strong" | "dim" — the skin engine maps
# these to actual colors.
Segment = Tuple[str, str, bool]

CONTEXT_BUDGET_DEFAULT = 200_000

# Context usage tiers (fraction of budget).
_TIER_GOOD = 0.60
_TIER_WARN = 0.85


def _context_tier(fraction: float) -> str:
    if fraction >= _TIER_WARN:
        return "warn"
    if fraction >= _TIER_GOOD:
        return "good"
    return "default"


def _format_tokens(n: Optional[int]) -> str:
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def build_statusline_segments(state: Optional[Dict[str, Any]] = None) -> List[Segment]:
    """Build the status bar segments from an agent state dict.

    The state dict may carry: model, provider, context_used,
    context_budget, turn, background_tasks, session_id. Missing keys
    degrade gracefully — the bar never crashes the TUI.
    """
    state = state or {}
    segments: List[Segment] = []

    # Model + provider
    model = state.get("model") or "?"
    provider = state.get("provider") or ""
    model_text = f"{model}" if not provider else f"{model} ({provider})"
    segments.append((model_text, "strong", True))

    # Context usage
    used = state.get("context_used")
    budget = state.get("context_budget") or CONTEXT_BUDGET_DEFAULT
    if used is not None:
        fraction = used / budget if budget else 0.0
        tier = _context_tier(fraction)
        segments.append(
            (f"ctx {_format_tokens(used)}/{_format_tokens(budget)}", tier, False)
        )

    # Turn / tasks
    turn = state.get("turn")
    if turn is not None:
        segments.append((f"turn {turn}", "dim", False))
    bg = state.get("background_tasks") or 0
    if bg:
        segments.append((f"{bg} bg", "warn", False))

    # Session
    session_id = state.get("session_id")
    if session_id:
        short = session_id[-8:] if len(session_id) > 8 else session_id
        segments.append((short, "dim", False))

    return segments


def render_statusline(segments: List[Segment], separator: str = " │ ") -> str:
    """Plain-text rendering of segments (for logs, tests, dumb terminals)."""
    return separator.join(text for text, _tier, _bold in segments)


def context_tier_for(fraction: float) -> str:
    """Public tier accessor for skin/color decisions."""
    return _context_tier(fraction)
