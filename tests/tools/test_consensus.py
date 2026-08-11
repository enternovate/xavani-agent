# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B04: multi-agent consensus tests."""

import pytest

from tools.consensus import (
    ConsensusEngine,
    measure_consensus,
    normalize_verdict,
)

pytestmark = pytest.mark.unit


# ── normalization ──────────────────────────────────────────────────


def test_normalize_verdict():
    assert normalize_verdict("YES.") == "yes"
    assert normalize_verdict("No") == "no"
    assert normalize_verdict(None) == ""
    assert normalize_verdict(123) == "123"
    assert normalize_verdict("  Approve  ") == "approve"


# ── consensus measurement ──────────────────────────────────────────


def test_unanimous_consensus():
    verdicts = [
        {"agent": "a", "verdict": "yes"},
        {"agent": "b", "verdict": "yes"},
        {"agent": "c", "verdict": "yes"},
    ]
    result = measure_consensus(verdicts)
    assert result["consensus_verdict"] == "yes"
    assert result["agreement_ratio"] == 1.0
    assert result["disagreement"] is False
    assert result["agents"] == 3


def test_majority_consensus():
    verdicts = [
        {"agent": "a", "verdict": "deploy"},
        {"agent": "b", "verdict": "deploy"},
        {"agent": "c", "verdict": "hold"},
    ]
    result = measure_consensus(verdicts)
    assert result["consensus_verdict"] == "deploy"
    assert result["agreement_ratio"] == pytest.approx(2 / 3, abs=1e-3)


def test_split_disagreement():
    verdicts = [
        {"agent": "a", "verdict": "yes"},
        {"agent": "b", "verdict": "no"},
    ]
    result = measure_consensus(verdicts)
    assert result["consensus_verdict"] is None  # 50/50, not majority
    assert result["disagreement"] is True
    assert result["agreement_ratio"] == 0.5


def test_format_variants_cluster_together():
    verdicts = [
        {"agent": "a", "verdict": "YES."},
        {"agent": "b", "verdict": "yes"},
        {"agent": "c", "verdict": "no"},
    ]
    result = measure_consensus(verdicts)
    assert result["consensus_verdict"] == "yes"
    assert result["clusters"][0]["count"] == 2


def test_too_few_agents_no_consensus():
    verdicts = [{"agent": "a", "verdict": "yes"}]
    result = measure_consensus(verdicts, min_agents=2)
    assert result["consensus_verdict"] is None
    assert result["agreement_ratio"] == 0.0


def test_empty_verdicts():
    result = measure_consensus([])
    assert result["consensus_verdict"] is None
    assert result["agents"] == 0


def test_empty_verdict_strings_ignored():
    verdicts = [
        {"agent": "a", "verdict": ""},
        {"agent": "b", "verdict": ""},
        {"agent": "c", "verdict": "yes"},
    ]
    result = measure_consensus(verdicts)
    assert result["consensus_verdict"] == "yes"


def test_cluster_agents_listed():
    verdicts = [
        {"agent": "a", "verdict": "yes"},
        {"agent": "b", "verdict": "yes"},
        {"agent": "c", "verdict": "no"},
    ]
    result = measure_consensus(verdicts)
    top = result["clusters"][0]
    assert set(top["agents"]) == {"a", "b"}


def test_engine_wrapper():
    engine = ConsensusEngine()
    result = engine.measure([{"agent": "a", "verdict": "x"}, {"agent": "b", "verdict": "x"}])
    assert result["consensus_verdict"] == "x"
