# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Collapse — the deterministic Born-rule measurement (v1.0.0 ①).

Given a measured superposition (branches with amplitude / expected_value / risk)
and the interference matrix, compute each branch's probability via a Born-rule-
style weight:

    weight_i = |amplitude_i|^2 · max(ev_i, eps) · (1 - 0.7 · eff_risk_i)

where ``eff_risk_i`` raises a branch's own risk by the risk it shares (through
interference) with the *other* high-amplitude branches. Probabilities are the
normalised weights. The chosen branch is the **argmax** (deterministic, with an
alphabetical id tie-break) — so the same inputs always collapse identically. No
RNG, no model calls (R10).
"""

from __future__ import annotations

from xavani_operator.quantum.state import Branch, Decision, Superposition

_EPS = 1e-6
_RISK_PENALTY = 0.7


def _effective_risk(idx: int, branches: list[Branch], interference: list[list[float]] | None) -> float:
    base = branches[idx].risk
    if not interference:
        return base
    n = len(branches)
    if n <= 1:
        return base
    # Positive correlation with another branch's risk adds to this branch's
    # effective risk (you're exposed the same way no matter which you pick);
    # negative correlation (a hedge) relieves it slightly.
    extra = 0.0
    for j in range(n):
        if j == idx:
            continue
        extra += interference[idx][j] * branches[j].risk
    extra /= n - 1
    return max(0.0, min(1.0, base + 0.5 * extra))


def measure(superposition: Superposition, interference: list[list[float]] | None = None) -> Decision:
    """Collapse the wavefunction to a Decision. Deterministic argmax (R10)."""
    branches = superposition.branches
    if not branches:
        raise ValueError("cannot measure an empty superposition")

    weights: list[float] = []
    for i, b in enumerate(branches):
        eff_risk = _effective_risk(i, branches, interference)
        w = (b.amplitude**2) * max(b.expected_value, _EPS) * max(0.0, 1.0 - _RISK_PENALTY * eff_risk)
        weights.append(w)

    total = sum(weights)
    if total <= 0:
        # Degenerate (everything scored out): fall back to amplitude^2 alone.
        weights = [b.amplitude**2 for b in branches]
        total = sum(weights) or 1.0

    probs = [w / total for w in weights]
    ranked = sorted(zip(branches, probs), key=lambda bp: (-bp[1], bp[0].id))
    chosen = ranked[0][0]
    return Decision(chosen=chosen, ranked=ranked)
