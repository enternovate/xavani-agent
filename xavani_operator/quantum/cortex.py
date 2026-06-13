# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Cortex — the orchestrator that runs the full quantum decision (v1.0.0 ①).

``decide`` ties the pieces together: superpose the top-K opportunities, simulate
each branch (filling expected_value / risk / signals from the Oracle), compute the
interference matrix, and collapse to a :class:`~xavani_operator.quantum.state.Decision`.

This is the single entry point the operator's classic ``decide.py`` will call
(behind a config flag) to upgrade a one-shot ranking into a measured decision.
Pure Python, deterministic, zero model calls (R10): same opportunities → same
decision.
"""

from __future__ import annotations

from xavani_operator.quantum.collapse import measure
from xavani_operator.quantum.interference import interference_matrix
from xavani_operator.quantum.simulate import rollout
from xavani_operator.quantum.state import Decision, superpose
from xavani_operator.types import Opportunity


def decide(
    opportunities: list[Opportunity],
    *,
    k: int = 5,
    seed: int | None = None,
    n_samples: int = 64,
) -> Decision:
    """Run superpose → simulate → interfere → collapse. Deterministic (R10)."""
    sp = superpose(opportunities, k=k, seed=seed)
    if not sp.branches:
        raise ValueError("no opportunities to decide between")

    for idx, branch in enumerate(sp.branches):
        out = rollout(branch.opportunity, n=n_samples, seed=sp.seed + idx)
        branch.expected_value = out.expected_value
        branch.risk = out.risk
        branch.signals = out.signals

    matrix = interference_matrix(sp.branches)
    return measure(sp, matrix)
