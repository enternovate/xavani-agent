# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""QUBO — frame a combinatorial decision for a (quantum) solver (v1.0.0 ①).

Some operator decisions are combinatorial: *which subset of candidate actions do
we commit to, given that some conflict?* That is a Quadratic Unconstrained Binary
Optimisation (QUBO) — the native form for quantum annealers (D-Wave) and QAOA on
gate machines. We minimise:

    energy(x) = sum_i linear_i · x_i  +  sum_{i<j} quadratic_ij · x_i · x_j

:func:`build_selection` encodes "maximise total value, but penalise picking a
conflicting pair" (linear = -value, quadratic = +penalty on conflicts). The same
QUBO is solved by the classical ``inspired`` backend or a real QPU — identical in
shape, so callers are backend-agnostic. Pure Python, zero-LLM (R10).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class QUBO:
    """A QUBO instance over ``n`` binary variables. Energy is minimised."""

    n: int
    linear: dict[int, float] = field(default_factory=dict)
    quadratic: dict[tuple[int, int], float] = field(default_factory=dict)

    def energy(self, bits: Sequence[int]) -> float:
        """Energy of a 0/1 assignment ``bits`` (lower is better)."""
        if len(bits) != self.n:
            raise ValueError(f"expected {self.n} bits, got {len(bits)}")
        e = 0.0
        for i, c in self.linear.items():
            e += c * bits[i]
        for (i, j), c in self.quadratic.items():
            e += c * bits[i] * bits[j]
        return e


def build_selection(
    values: Sequence[float],
    conflicts: Sequence[tuple[int, int]] | None = None,
    *,
    penalty: float | None = None,
) -> QUBO:
    """Build a "maximise value, avoid conflicting pairs" QUBO.

    ``values[i]`` is the value of selecting item ``i``; ``conflicts`` lists pairs
    that should not both be selected. The penalty defaults to more than the total
    value, so violating a conflict can never pay off.
    """
    n = len(values)
    linear = {i: -float(values[i]) for i in range(n)}
    pen = penalty if penalty is not None else (sum(abs(float(v)) for v in values) + 1.0)
    quadratic: dict[tuple[int, int], float] = {}
    for i, j in conflicts or []:
        a, b = sorted((int(i), int(j)))
        quadratic[(a, b)] = quadratic.get((a, b), 0.0) + pen
    return QUBO(n=n, linear=linear, quadratic=quadratic)
