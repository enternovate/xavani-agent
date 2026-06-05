# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic decision step (v0.7.0 operator U19).

Given the ranked opportunities from ``opportunities.detect``, choose the single
:class:`~xavani_operator.types.Intent` the operator will act on this cycle. This
is **pure Python, zero model calls** (R10): the choice is the top-scoring
opportunity with a stable tie-break (lowest id), so the same state always yields
the same decision. Budget/quiet-hours gating happens at propose time (M2) and in
the loop (M3); here we just pick.
"""

from __future__ import annotations

from xavani_operator.types import Intent, Opportunity


def decide(opportunities: list[Opportunity], config) -> Intent | None:
    """Pick the top opportunity → an Intent, or ``None`` if there are none."""
    if not opportunities:
        return None
    top = sorted(opportunities, key=lambda o: (-o.score, o.id))[0]
    return Intent(opportunity=top)
