# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Interference — how candidate strategies reinforce or cancel each other (v1.0.0 ①).

Real decisions aren't independent. Two strategies that share a failure mode
(the same downfall signals) **reinforce** that risk — picking either leaves you
exposed the same way, so the shared risk is amplified (constructive interference
on the risk axis). Two strategies with no shared risk and different workstreams
**hedge** — they cancel some risk (destructive interference).

``interference_matrix`` returns a symmetric NxN matrix of correlations in
``[-1, 1]`` (diagonal 1.0), computed from the Jaccard overlap of each branch's
risk signals. Pure Python, deterministic, zero-LLM (R10).
"""

from __future__ import annotations

from xavani_operator.quantum.state import Branch

_HEDGE = -0.2  # mild destructive interference for genuinely complementary branches


def interference_matrix(branches: list[Branch]) -> list[list[float]]:
    """Symmetric correlation matrix from shared downfall signals. Deterministic."""
    n = len(branches)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        m[i][i] = 1.0
        for j in range(i + 1, n):
            si = set(branches[i].signals)
            sj = set(branches[j].signals)
            union = si | sj
            jaccard = (len(si & sj) / len(union)) if union else 0.0
            if jaccard > 0:
                corr = jaccard  # shared failure mode → reinforce risk
            elif branches[i].opportunity.workstream != branches[j].opportunity.workstream:
                corr = _HEDGE  # no shared risk + different workstream → hedge
            else:
                corr = 0.0
            m[i][j] = corr
            m[j][i] = corr
    return m
