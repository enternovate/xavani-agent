# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Oracle core — patterns + consequence projection (v1.0.0 ②).

Covers: corpus loads with the seeded figures; the matcher finds the right
downfall pattern; consequence projection is deterministic; downfall-shaped
contexts carry more risk than benign ones; and the whole module is **zero-LLM**
(static AST check mirroring ``tests/operator/test_no_llm.py``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import xavani_wisdom as oracle
from xavani_wisdom import consequence, patterns

REPO = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# Corpus + matcher
# --------------------------------------------------------------------------- #
def test_corpus_loads_with_seed_figures() -> None:
    corpus = patterns.load_corpus()
    figures = {p.figure for p in corpus}
    assert "King Solomon" in figures
    assert "Jeff Bezos" in figures
    assert "Warren Buffett" in figures
    # Both rise and fall are represented.
    kinds = {p.kind for p in corpus}
    assert {"ascent", "downfall"} <= kinds
    # Every pattern has an id and is attributed (no anonymous lessons).
    assert all(p.id for p in corpus)
    assert all(p.sources for p in corpus)


def test_required_fields_present() -> None:
    for p in patterns.load_corpus():
        assert p.kind in {"ascent", "downfall"}, p.id
        assert p.the_lesson, p.id


def test_match_finds_solomon_overreach() -> None:
    text = "We are at our peak — let's scale fast, raise more, defer cost and expand aggressively."
    ranked = patterns.match(text, kind="downfall")
    assert ranked[0][1] > 0  # top match has positive score
    top_ids = [p.id for p, score in ranked if score > 0]
    assert "solomon-downfall-overreach" in top_ids


def test_match_phrase_keyword_cash_cow() -> None:
    # "cash cow" is a two-word keyword; substring matching should catch it.
    ranked = patterns.match("protect the cash cow and ignore the disruption", kind="downfall")
    top = ranked[0][0]
    assert top.id == "kodak-downfall-disruption-denial"


def test_match_deterministic() -> None:
    text = "leverage everything, we cannot lose, bet big"
    a = [(p.id, s) for p, s in patterns.match(text)]
    b = [(p.id, s) for p, s in patterns.match(text)]
    assert a == b


# --------------------------------------------------------------------------- #
# Consequence projection
# --------------------------------------------------------------------------- #
def test_project_deterministic() -> None:
    ctx = {"text": "scale fast and expand", "reversible": False, "cost": 0.8, "scope": "public"}
    r1 = consequence.project(ctx)
    r2 = consequence.project(ctx)
    assert r1.to_dict() == r2.to_dict()


def test_downfall_context_is_riskier_than_benign() -> None:
    benign = consequence.project(
        {"text": "write a unit test for the parser", "reversible": True, "scope": "local"}
    )
    risky = consequence.project(
        {
            "text": "borrow heavily, go all in, we cannot lose — scale fast and ignore the base rate",
            "reversible": False,
            "cost": 0.9,
            "scope": "public",
        }
    )
    assert risky.risk > benign.risk
    assert risky.tail_risk > benign.tail_risk
    assert risky.reversibility < benign.reversibility
    assert risky.base_rate_flag is True
    assert benign.base_rate_flag is False


def test_detect_downfall_returns_signals() -> None:
    signals = consequence.detect_downfall(
        {"text": "hide the bad numbers and inflate the metrics at any cost"}
    )
    assert "fraud" in signals or "metric_theatre" in signals


def test_project_clamps_to_unit_interval() -> None:
    r = consequence.project({"text": "x", "cost": 5.0, "value": 9.0, "reversible": False})
    for v in (r.reversibility, r.tail_risk, r.risk, r.expected_value):
        assert 0.0 <= v <= 1.0


def test_public_export_surface() -> None:
    assert hasattr(oracle, "project")
    assert hasattr(oracle, "match")
    assert hasattr(oracle, "WisdomPattern")
    assert hasattr(oracle, "detect_downfall")


# --------------------------------------------------------------------------- #
# R10 — the Oracle decision path makes ZERO LLM calls (static AST check)
# --------------------------------------------------------------------------- #
_WISDOM_MODULES = [
    "xavani_wisdom/__init__.py",
    "xavani_wisdom/patterns.py",
    "xavani_wisdom/consequence.py",
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


def test_oracle_is_zero_llm() -> None:
    for rel in _WISDOM_MODULES:
        path = REPO / rel
        assert path.exists(), rel
        for module in _imported_modules(path):
            root = module.split(".")[0]
            assert root not in _FORBIDDEN_ROOTS, f"{rel} imports LLM client '{module}' (R10)"
            assert not any(s in module for s in _FORBIDDEN_SUBSTRINGS), f"{rel} imports '{module}' (R10)"
