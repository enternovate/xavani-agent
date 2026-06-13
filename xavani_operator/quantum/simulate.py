# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Branch simulation — seeded Monte-Carlo rollout of an opportunity (v1.0.0 ①).

For each branch the Cortex needs an expected value and a risk. We derive a
*decision context* from the opportunity, ask the Oracle (major ②) to project its
consequences (deterministic), then sample ``n`` outcome scenarios around that
projection with a **seeded** RNG so the result is reproducible. The risk returned
blends the Oracle's structural risk with the simulated tail (fraction of bad
draws), so a strategy that is fragile in simulation is penalised.

Pure Python, zero model calls (R10): same ``(opportunity, seed)`` → same Outcome.
"""

from __future__ import annotations

import random

from xavani_operator.quantum.state import Outcome
from xavani_operator.types import Opportunity
from xavani_wisdom.consequence import project

_BAD_OUTCOME = 0.3  # a sampled value below this counts toward the tail


def _ctx_from_opportunity(opp: Opportunity) -> dict:
    """Map an operator Opportunity onto a consequence-projection context."""
    payload = opp.payload or {}
    return {
        "text": " ".join([str(opp.rationale or ""), str(opp.kind or ""), str(opp.workstream or "")]),
        "value": float(opp.score),
        "reversible": bool(payload.get("reversible", True)),
        "cost": float(payload.get("cost", 0.0)),
        "scope": str(payload.get("scope", "local")),
        "horizon": str(payload.get("horizon", "quarter")),
        "signals": list(payload.get("signals", [])),
    }


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def rollout(opportunity: Opportunity, *, n: int = 64, seed: int = 0) -> Outcome:
    """Simulate ``n`` outcome scenarios for an opportunity. Deterministic given seed."""
    base = project(_ctx_from_opportunity(opportunity))
    rng = random.Random(seed)

    # Spread grows with risk: a risky branch has a wider, heavier-tailed outcome cloud.
    spread = 0.08 + 0.30 * base.risk
    samples = [_clamp(base.expected_value + rng.gauss(0.0, spread)) for _ in range(max(1, n))]

    mean_ev = sum(samples) / len(samples)
    tail = sum(1 for s in samples if s < _BAD_OUTCOME) / len(samples)
    risk = _clamp(0.5 * base.risk + 0.5 * tail)

    return Outcome(expected_value=mean_ev, risk=risk, signals=list(base.downfall_signals))
