# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Quantum Decision Cortex (v1.0.0 ①).

Covers: superposition normalisation; deterministic collapse; the cortex prefers a
safe high-value branch over a downfall-shaped one; interference reinforces shared
risk; the QUBO solver is correct and respects conflicts; backend selection falls
back to the classical solver without credentials; outcome records round-trip; and
the whole package is zero-LLM (static AST check).
"""

from __future__ import annotations

import ast
from pathlib import Path

import xavani_operator.quantum as q
from xavani_operator.quantum import backends, outcome_patterns, qubo
from xavani_operator.types import Opportunity

REPO = Path(__file__).resolve().parents[3]


def _safe_and_risky() -> list[Opportunity]:
    return [
        Opportunity(
            id="safe-ship-tests",
            kind="fix",
            workstream="build",
            score=0.8,
            rationale="write tests, customer focus, long term, margin of safety",
            payload={"reversible": True, "cost": 0.1, "scope": "local"},
        ),
        Opportunity(
            id="risky-leveraged-bet",
            kind="bet",
            workstream="promote",
            score=0.8,
            rationale="borrow heavily, go all in, we cannot lose, scale fast and ignore the base rate",
            payload={"reversible": False, "cost": 0.9, "scope": "public"},
        ),
    ]


# --------------------------------------------------------------------------- #
# Superposition + collapse
# --------------------------------------------------------------------------- #
def test_superpose_is_normalized() -> None:
    opps = _safe_and_risky()
    sp = q.superpose(opps, k=5, seed=1)
    norm = sum(b.amplitude**2 for b in sp.branches)
    assert abs(norm - 1.0) < 1e-9


def test_decide_is_deterministic() -> None:
    opps = _safe_and_risky()
    d1 = q.decide(opps, seed=42)
    d2 = q.decide(opps, seed=42)
    assert d1.chosen.id == d2.chosen.id
    assert d1.probabilities == d2.probabilities


def test_decide_prefers_safe_over_downfall() -> None:
    d = q.decide(_safe_and_risky(), seed=7)
    assert d.chosen.id == "safe-ship-tests"
    assert d.probabilities["safe-ship-tests"] > d.probabilities["risky-leveraged-bet"]
    # The risky branch carries downfall signals; the safe one should not.
    risky = next(b for b, _ in d.ranked if b.id == "risky-leveraged-bet")
    assert risky.signals  # leverage / overextension flagged
    assert risky.risk > 0.0


def test_collapse_summary_renders() -> None:
    d = q.decide(_safe_and_risky(), seed=3)
    text = d.summary()
    assert "chosen:" in text
    assert "safe-ship-tests" in text


# --------------------------------------------------------------------------- #
# Interference
# --------------------------------------------------------------------------- #
def test_interference_reinforces_shared_risk() -> None:
    a = q.Branch(id="a", opportunity=_safe_and_risky()[1], amplitude=0.7, signals=["leverage", "hubris"])
    b = q.Branch(id="b", opportunity=_safe_and_risky()[1], amplitude=0.7, signals=["leverage"])
    m = q.interference_matrix([a, b])
    assert m[0][0] == 1.0 and m[1][1] == 1.0
    assert m[0][1] == m[1][0]  # symmetric
    assert m[0][1] > 0.0  # shared "leverage" → positive (reinforcing) correlation


# --------------------------------------------------------------------------- #
# QUBO + backends
# --------------------------------------------------------------------------- #
def test_qubo_inspired_matches_bruteforce_and_respects_conflict() -> None:
    # Items 0 and 1 are high value but conflict; item 2 is lower value, no conflict.
    values = [1.0, 1.0, 0.6]
    conflicts = [(0, 1)]
    problem = qubo.build_selection(values, conflicts)
    backend = backends.select_backend(env={})
    bits = backend.solve(problem, seed=0)

    # Independent brute-force optimum over all assignments.
    best = min(
        ([(m >> i) & 1 for i in range(problem.n)] for m in range(1 << problem.n)),
        key=problem.energy,
    )
    assert problem.energy(bits) == problem.energy(best)
    # The conflicting pair is never both selected at the optimum.
    assert not (bits[0] == 1 and bits[1] == 1)
    # Item 2 (no conflict, positive value) is always worth taking.
    assert bits[2] == 1


def test_select_backend_falls_back_to_inspired() -> None:
    assert backends.select_backend(env={}).name == "inspired"
    # Credentials are detected...
    assert backends.available_quantum_providers({"DWAVE_API_TOKEN": "x"}) == ["dwave"]
    # ...but with no SDK module present we still fall back to the classical solver.
    assert backends.select_backend(env={"DWAVE_API_TOKEN": "x"}).name == "inspired"


# --------------------------------------------------------------------------- #
# Outcome patterns (the "compare outcomes of decisions" loop)
# --------------------------------------------------------------------------- #
def test_outcome_record_roundtrip_and_compare(tmp_path) -> None:
    path = tmp_path / "outcomes.json"
    d = q.decide(_safe_and_risky(), seed=5)
    outcome_patterns.record(path, d, realized=0.9, decision_id="cycle-1")
    outcome_patterns.record(path, d, realized=0.7, decision_id="cycle-2")

    loaded = outcome_patterns.load(path)
    assert len(loaded) == 2
    assert loaded[0].decision_id == "cycle-1"
    assert loaded[0].chosen_id == d.chosen.id

    means = outcome_patterns.compare(loaded)
    assert abs(means[d.chosen.id] - 0.8) < 1e-9  # (0.9 + 0.7) / 2


# --------------------------------------------------------------------------- #
# R10 — the Cortex makes ZERO LLM calls (static AST check)
# --------------------------------------------------------------------------- #
_MODULES = [
    "xavani_operator/quantum/__init__.py",
    "xavani_operator/quantum/state.py",
    "xavani_operator/quantum/simulate.py",
    "xavani_operator/quantum/interference.py",
    "xavani_operator/quantum/collapse.py",
    "xavani_operator/quantum/cortex.py",
    "xavani_operator/quantum/qubo.py",
    "xavani_operator/quantum/outcome_patterns.py",
    "xavani_operator/quantum/backends/__init__.py",
    "xavani_operator/quantum/backends/inspired.py",
]
_FORBIDDEN_ROOTS = {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq", "together"}
_FORBIDDEN_SUBSTRINGS = ("openrouter_client", "xai_http", "generativeai")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def test_quantum_cortex_is_zero_llm() -> None:
    for rel in _MODULES:
        path = REPO / rel
        assert path.exists(), rel
        for module in _imported_modules(path):
            root = module.split(".")[0]
            assert root not in _FORBIDDEN_ROOTS, f"{rel} imports LLM client '{module}' (R10)"
            assert not any(s in module for s in _FORBIDDEN_SUBSTRINGS), f"{rel} imports '{module}' (R10)"
