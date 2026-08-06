# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Context-budget governor UI thresholds (harness item 4).

Extends B02: warn at 85% of the context budget with a compaction
suggestion, hard-block new tools at 95%. Pure threshold logic — the
conversation loop and statusline call these helpers.

The existing ``agent/budget_governor.py`` tracks session cost; this module
owns the *context* (token) budget surface used by /usage and statusline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

WARN_RATIO = 0.85
HARD_BLOCK_RATIO = 0.95


@dataclass(frozen=True)
class BudgetStatus:
    """The computed budget state for one surface."""
    used_tokens: int
    limit_tokens: int
    ratio: float
    level: str  # "ok" | "warn" | "block"
    suggestion: str


def compute_budget_status(used_tokens: int, limit_tokens: int) -> BudgetStatus:
    """Classify usage against the context budget.

    ratio >= 0.95 -> block (no new tools), >= 0.85 -> warn (suggest
    compaction), else ok. A non-positive limit returns ok with no
    suggestion (budget disabled).
    """
    if limit_tokens <= 0:
        return BudgetStatus(
            used_tokens=used_tokens,
            limit_tokens=limit_tokens,
            ratio=0.0,
            level="ok",
            suggestion="",
        )
    ratio = used_tokens / limit_tokens
    if ratio >= HARD_BLOCK_RATIO:
        return BudgetStatus(
            used_tokens=used_tokens,
            limit_tokens=limit_tokens,
            ratio=ratio,
            level="block",
            suggestion="Context at 95%+ — /compact required before new tool calls.",
        )
    if ratio >= WARN_RATIO:
        return BudgetStatus(
            used_tokens=used_tokens,
            limit_tokens=limit_tokens,
            ratio=ratio,
            level="warn",
            suggestion=f"Context at {ratio * 100:.0f}% — /compact recommended.",
        )
    return BudgetStatus(
        used_tokens=used_tokens,
        limit_tokens=limit_tokens,
        ratio=ratio,
        level="ok",
        suggestion="",
    )


def should_block_new_tools(status: BudgetStatus) -> bool:
    """True when the budget is at the hard-block level."""
    return status.level == "block"


def status_to_dict(status: BudgetStatus) -> Dict[str, Any]:
    """Serialise the status for /usage and the web server."""
    return {
        "used_tokens": status.used_tokens,
        "limit_tokens": status.limit_tokens,
        "ratio": round(status.ratio, 4),
        "level": status.level,
        "suggestion": status.suggestion,
    }
