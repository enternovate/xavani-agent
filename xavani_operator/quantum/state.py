# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Quantum state — Branch / Superposition / Outcome / Decision + superpose (v1.0.0 ①).

These are the data structures the Cortex measures. A :class:`Branch` is one
candidate strategy (wrapping an operator :class:`~xavani_operator.types.Opportunity`)
carrying a real **amplitude** whose square is its pre-measurement weight, plus the
``expected_value`` / ``risk`` / ``signals`` that ``simulate`` fills in. A
:class:`Superposition` is the set of branches plus a deterministic seed.

``superpose`` builds the initial state from scored opportunities: amplitudes are
the square-roots of the normalised scores, so ``sum(|amplitude|^2) == 1`` — a
proper (real) state vector. Deterministic, zero-LLM (R10).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from xavani_operator.types import Opportunity


@dataclass
class Branch:
    """One candidate strategy in the superposition (mutable: simulate fills it in)."""

    id: str
    opportunity: Opportunity
    amplitude: float  # real, >= 0; |amplitude|^2 is the probability weight
    expected_value: float = 0.0
    risk: float = 0.0
    signals: list[str] = field(default_factory=list)


@dataclass
class Superposition:
    """The set of candidate branches plus the deterministic RNG seed."""

    branches: list[Branch]
    seed: int


@dataclass
class Outcome:
    """The simulated result of one branch (mean expected value + tail risk)."""

    expected_value: float
    risk: float
    signals: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """The collapsed decision: the chosen branch + the full ranked wavefunction."""

    chosen: Branch
    ranked: list[tuple[Branch, float]]  # (branch, probability) desc; sums ~1

    @property
    def probabilities(self) -> dict[str, float]:
        return {b.id: p for b, p in self.ranked}

    def summary(self) -> str:
        """A one-line-per-branch readable rendering of the collapse (for the CLI)."""
        lines = [f"chosen: {self.chosen.id}"]
        for b, p in self.ranked:
            mark = "►" if b.id == self.chosen.id else " "
            lines.append(
                f" {mark} {b.id:<28} p={p:5.3f}  ev={b.expected_value:4.2f}  "
                f"risk={b.risk:4.2f}  amp={b.amplitude:4.2f}"
            )
        return "\n".join(lines)


def _stable_seed(opportunities: list[Opportunity]) -> int:
    """A deterministic seed derived from the opportunity ids (not Python's salted hash)."""
    key = ",".join(sorted(o.id for o in opportunities))
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def superpose(
    opportunities: list[Opportunity],
    *,
    k: int = 5,
    seed: int | None = None,
) -> Superposition:
    """Build the initial superposition from the top-``k`` scored opportunities.

    Amplitudes are ``sqrt(score / sum_scores)`` so ``sum(|amplitude|^2) == 1``.
    Selection and ordering are deterministic (score desc, then id). Zero-LLM.
    """
    ranked = sorted(opportunities, key=lambda o: (-float(o.score), o.id))[: max(0, k)]
    if not ranked:
        return Superposition(branches=[], seed=seed if seed is not None else 0)

    total = sum(max(0.0, float(o.score)) for o in ranked)
    n = len(ranked)
    branches: list[Branch] = []
    for o in ranked:
        if total > 0:
            weight = max(0.0, float(o.score)) / total
        else:
            weight = 1.0 / n  # all-zero scores → uniform
        branches.append(Branch(id=o.id, opportunity=o, amplitude=math.sqrt(weight)))

    return Superposition(
        branches=branches,
        seed=seed if seed is not None else _stable_seed(ranked),
    )
