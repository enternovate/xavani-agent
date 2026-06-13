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


def _quantum_enabled(config) -> bool:
    """Whether the Quantum Decision Cortex is turned on for this config.

    Opt-in and default-OFF so existing behaviour is unchanged unless the user
    enables it. Accepts ``config.quantum`` as a bool, an object with ``.enabled``,
    a mapping with ``"enabled"``, or a flat ``config.quantum_enabled`` flag.
    """
    q = getattr(config, "quantum", None)
    if isinstance(q, bool):
        return q
    if isinstance(q, dict):
        return bool(q.get("enabled", False))
    if q is not None and hasattr(q, "enabled"):
        return bool(q.enabled)
    return bool(getattr(config, "quantum_enabled", False))


def decide(opportunities: list[Opportunity], config) -> Intent | None:
    """Pick the opportunity to act on → an Intent, or ``None`` if there are none.

    Classic mode (default): the top-scoring opportunity with a stable tie-break.
    With the Quantum Decision Cortex enabled (``config.quantum.enabled``), the
    choice is the **collapse** of a superposition that simulates each candidate's
    consequences and lets correlated risks interfere — so the operator steers away
    from high-score-but-fragile moves. Both paths are pure Python (R10).
    """
    if not opportunities:
        return None
    if _quantum_enabled(config):
        # Lazy import: the Cortex is only loaded when actually enabled.
        from xavani_operator.quantum import decide as quantum_decide

        decision = quantum_decide(opportunities)
        return Intent(opportunity=decision.chosen.opportunity)
    top = sorted(opportunities, key=lambda o: (-o.score, o.id))[0]
    return Intent(opportunity=top)
