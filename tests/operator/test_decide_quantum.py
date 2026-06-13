# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""The Quantum Cortex wiring into operator.decide (v1.0.0 ①).

Confirms decide() keeps its classic top-score behaviour by default, but when the
quantum flag is enabled it routes through the Cortex — steering away from a
high-score-but-downfall opportunity toward the safer, reversible one.
"""

from __future__ import annotations

from dataclasses import dataclass

from xavani_operator.decide import decide
from xavani_operator.types import Opportunity


@dataclass
class _Cfg:
    quantum_enabled: bool = False


def _risky_top_and_safe() -> list[Opportunity]:
    return [
        Opportunity(
            id="risky-top",
            kind="bet",
            workstream="promote",
            score=0.92,  # highest score
            rationale="borrow heavily, go all in, we cannot lose, scale fast, ignore the base rate",
            payload={"reversible": False, "cost": 0.95, "scope": "public"},
        ),
        Opportunity(
            id="safe-second",
            kind="fix",
            workstream="build",
            score=0.74,  # lower score
            rationale="write tests, customer focus, long term, margin of safety",
            payload={"reversible": True, "cost": 0.1, "scope": "local"},
        ),
    ]


def test_classic_decide_picks_top_score_by_default() -> None:
    intent = decide(_risky_top_and_safe(), _Cfg(quantum_enabled=False))
    assert intent is not None
    assert intent.opportunity.id == "risky-top"  # classic = highest score


def test_quantum_decide_steers_away_from_downfall() -> None:
    intent = decide(_risky_top_and_safe(), _Cfg(quantum_enabled=True))
    assert intent is not None
    # The Cortex + Oracle down-weight the leveraged, irreversible, base-rate-denying
    # option even though it scored highest, and choose the safe reversible move.
    assert intent.opportunity.id == "safe-second"


def test_decide_none_on_empty() -> None:
    assert decide([], _Cfg(quantum_enabled=True)) is None
