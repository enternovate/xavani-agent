# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Quantum Decision Cortex — superposition → simulate → interfere → collapse (v1.0.0 ①).

The operator's classic ``decide`` picks the single top-scored opportunity. The
Cortex instead holds the top-K candidates in a **superposition**, **simulates**
each one's outcomes (using the Oracle's consequence projection, major ②), lets
correlated risks **interfere**, then performs a deterministic **Born-rule
measurement** to collapse the wavefunction onto the best decision.

It is quantum-*inspired* and **pure Python, zero model calls** (R10): the same
inputs always collapse to the same decision. A genuine quantum accelerator
(Qiskit / IBM / Braket / D-Wave) is available for the combinatorial sub-problem
(``qubo`` + ``backends``) and activates only when its SDK *and* credentials are
present — exactly like a model-provider key — otherwise the always-on classical
``inspired`` backend is used.

Public surface:
    Branch, Superposition, Outcome, Decision, superpose   -- state.py
    rollout                                               -- simulate.py
    interference_matrix                                   -- interference.py
    measure                                               -- collapse.py
    decide                                                -- cortex.py  (the orchestrator)
"""

from __future__ import annotations

from xavani_operator.quantum.collapse import measure
from xavani_operator.quantum.cortex import decide
from xavani_operator.quantum.interference import interference_matrix
from xavani_operator.quantum.simulate import rollout
from xavani_operator.quantum.state import (
    Branch,
    Decision,
    Outcome,
    Superposition,
    superpose,
)

__all__ = [
    "Branch",
    "Superposition",
    "Outcome",
    "Decision",
    "superpose",
    "rollout",
    "interference_matrix",
    "measure",
    "decide",
]
