# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""IBM Quantum backend — optional, requires qiskit-ibm-runtime and IBM_QUANTUM_TOKEN.

This backend is only selected when IBM_QUANTUM_TOKEN is set AND qiskit-ibm-runtime
is importable. Falls back gracefully to the classical 'inspired' backend otherwise.
"""

from __future__ import annotations

from xavani_operator.quantum.qubo import QUBO


class IBMQuantumBackend:
    """IBM Quantum backend using Qiskit Runtime."""

    name = "ibm_quantum"

    def __init__(self):
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            from qiskit.quantum_info import SparsePauliOp
            from qiskit_aer import AerSimulator
            from qiskit import QuantumCircuit
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
            from qiskit_ibm_runtime import SamplerV2 as Sampler
        except Exception as e:  # pragma: no cover - optional dependency
            raise ImportError(f"IBM Quantum backend unavailable: {e}")

    def solve(self, qubo: QUBO, *, seed: int = 0, iters: int = 4000) -> list[int]:
        """Solve a QUBO using IBM Quantum hardware/simulator.
        
        Note: For now, falls back to classical annealing. Full QAOA/VQE implementation
        would require significant additional code. The interface is present for when
        the SDK and credentials are available.
        """
        # TODO: Implement QAOA or VQE for QUBO on IBM Quantum
        # For now, delegate to classical solver to maintain interface
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
    """Factory function for the IBM Quantum backend."""
    try:
        return IBMQuantumBackend()
    except ImportError:
        return None
