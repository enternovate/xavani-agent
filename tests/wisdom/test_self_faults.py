# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for self-fault learning — recurring mistakes become watch-patterns (v1.0.0 ②)."""

from __future__ import annotations

from xavani_wisdom import self_faults
from xavani_wisdom.consequence import detect_downfall


def _entry(assumption: str) -> dict:
    return {"wasted_effort": [{"assumption": assumption, "cost": "time"}]}


def test_recurring_assumption_becomes_pattern() -> None:
    entries = [
        _entry("I underestimated the deadline again"),
        _entry("underestimated the scope of the migration"),
    ]
    patterns = self_faults.learn_from_errors(entries, min_repeats=2)
    ids = {p.id for p in patterns}
    assert "self-fault-underestimated" in ids
    p = next(p for p in patterns if p.id == "self-fault-underestimated")
    assert p.kind == "downfall"
    assert "underestimated" in p.keywords
    assert "self_fault" in p.signals


def test_single_occurrence_makes_no_pattern() -> None:
    entries = [_entry("the build server was flaky today")]
    assert self_faults.learn_from_errors(entries, min_repeats=2) == []


def test_learn_is_deterministic() -> None:
    entries = [_entry("overestimated demand"), _entry("overestimated runway")]
    a = [p.id for p in self_faults.learn_from_errors(entries)]
    b = [p.id for p in self_faults.learn_from_errors(entries)]
    assert a == b


def test_learned_pattern_is_detectable_by_oracle() -> None:
    # A personalised fault pattern should then be matchable as a downfall signal.
    entries = [_entry("I underestimated the deadline"), _entry("underestimated the effort")]
    learned = self_faults.learn_from_errors(entries)
    assert learned, "expected at least one learned pattern"
    # Feed the learned patterns into the detector against a new, similar context.
    from xavani_wisdom.patterns import load_corpus

    corpus = load_corpus() + learned
    signals = detect_downfall({"text": "I think I underestimated this deadline too"}, corpus)
    assert any(s.startswith("repeat_") or s == "self_fault" for s in signals)
