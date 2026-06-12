# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Inspired backend — the always-on classical QUBO solver (v1.0.0 ①).

The default backend, requiring no SDK or credentials. For small problems it solves
**exactly** by enumeration (so the answer is provably optimal); for larger ones it
runs **simulated annealing** — the classical cousin of quantum annealing — with a
seeded RNG so results are reproducible. The interface (``solve(qubo) -> bits``)
matches what the optional real-QPU backends will expose, so callers never branch
on which backend they got.

Pure Python, deterministic given the seed, zero-LLM (R10).
"""

from __future__ import annotations

import math
import random

from xavani_operator.quantum.qubo import QUBO

_EXACT_MAX_VARS = 18  # 2**18 = 262144 — fast to enumerate; above this, anneal.


class InspiredBackend:
    """Classical QUBO solver: exact for small n, simulated annealing otherwise."""

    name = "inspired"

    def solve(self, qubo: QUBO, *, seed: int = 0, iters: int = 4000) -> list[int]:
        if qubo.n == 0:
            return []
        if qubo.n <= _EXACT_MAX_VARS:
            return _brute_force(qubo)
        return _anneal(qubo, seed=seed, iters=iters)


def _brute_force(qubo: QUBO) -> list[int]:
    """Exact minimiser by enumerating all 2**n assignments. Deterministic."""
    best_bits: list[int] | None = None
    best_energy = math.inf
    for mask in range(1 << qubo.n):
        bits = [(mask >> i) & 1 for i in range(qubo.n)]
        e = qubo.energy(bits)
        if e < best_energy:
            best_energy = e
            best_bits = bits
    return best_bits or [0] * qubo.n


def _anneal(qubo: QUBO, *, seed: int, iters: int) -> list[int]:
    """Seeded simulated annealing. Reproducible for a given seed."""
    rng = random.Random(seed)
    bits = [rng.randint(0, 1) for _ in range(qubo.n)]
    energy = qubo.energy(bits)
    best_bits, best_energy = list(bits), energy

    for step in range(max(1, iters)):
        temp = max(1e-3, 1.0 - step / iters)
        i = rng.randrange(qubo.n)
        bits[i] ^= 1
        new_energy = qubo.energy(bits)
        delta = new_energy - energy
        if delta <= 0 or rng.random() < math.exp(-delta / temp):
            energy = new_energy
            if energy < best_energy:
                best_energy = energy
                best_bits = list(bits)
        else:
            bits[i] ^= 1  # reject: revert the flip
    return best_bits
