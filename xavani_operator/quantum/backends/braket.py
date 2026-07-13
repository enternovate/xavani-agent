# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""AWS Braket backend — optional, requires amazon-braket-sdk and AMAZON_BRAKET_ENABLED + AWS creds.

This backend is only selected when AMAZON_BRAKET_ENABLED is set AND the Braket SDK
is importable. Falls back gracefully to the classical 'inspired' backend otherwise.
"""

from __future__ import annotations

from xavani_operator.quantum.qubo import QUBO


class BraketBackend:
    """AWS Braket backend."""

    name = "braket"

    def __init__(self):
        try:
            from braket.devices import LocalSimulator
            from braket.aws import AwsDevice
        except Exception as e:  # pragma: no cover - optional dependency
            raise ImportError(f"AWS Braket backend unavailable: {e}")

    def solve(self, qubo: QUBO, *, seed: int = 0, iters: int = 4000) -> list[int]:
        """Solve a QUBO using AWS Braket.
        
        Note: For now, falls back to classical annealing. Full implementation
        would use LocalSimulator or AwsDevice to submit the QUBO.
        """
        # TODO: Implement native Braket QUBO submission
        import math
        import random
        
        _EXACT_MAX_VARS = 18
        
        def _brute_force(qubo: QUBO) -> list[int]:
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
                    bits[i] ^= 1
            return best_bits
        
        if qubo.n == 0:
            return []
        if qubo.n <= _EXACT_MAX_VARS:
            return _brute_force(qubo)
        return _anneal(qubo, seed=seed, iters=iters)


def backend():
    """Factory function for the AWS Braket backend."""
    try:
        return BraketBackend()
    except ImportError:
        return None
