# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B11: tool complementarity matrix tests."""

import pytest

from tools.complementarity import MIN_PAIR_OCCURRENCES, ComplementarityMatrix

pytestmark = pytest.mark.integration


@pytest.fixture
def matrix(tmp_path):
    return ComplementarityMatrix(home=tmp_path)


# ── recording ──────────────────────────────────────────────────────


def test_record_run_counts_pairs(matrix):
    matrix.record_run(["read_file", "patch", "terminal"], success=True)
    assert matrix.run_count() == 1
    assert matrix.pair_stats("read_file", "patch")["occurrences"] == 1
    assert matrix.pair_stats("read_file", "terminal")["occurrences"] == 1


def test_single_tool_run_ignored(matrix):
    matrix.record_run(["read_file"], success=True)
    assert matrix.run_count() == 0


def test_empty_run_ignored(matrix):
    matrix.record_run([], success=True)
    assert matrix.run_count() == 0


def test_successes_tracked_per_pair(matrix):
    matrix.record_run(["a", "b"], success=True)
    matrix.record_run(["a", "b"], success=False)
    stats = matrix.pair_stats("a", "b")
    assert stats["occurrences"] == 2
    assert stats["successes"] == 1
    assert stats["success_rate"] == 0.5


def test_pair_key_order_independent(matrix):
    matrix.record_run(["a", "b"], success=True)
    assert matrix.pair_stats("a", "b")["occurrences"] == 1
    assert matrix.pair_stats("b", "a")["occurrences"] == 1


def test_unknown_pair(matrix):
    assert matrix.pair_stats("x", "y")["success_rate"] is None


# ── complements ────────────────────────────────────────────────────


def test_complements_ranked_by_success(matrix):
    for _ in range(3):
        matrix.record_run(["read_file", "good_pair"], success=True)
    for _ in range(3):
        matrix.record_run(["read_file", "bad_pair"], success=False)
    complements = matrix.complements("read_file")
    assert complements[0][0] == "good_pair"
    assert complements[0][1] == 1.0
    assert complements[1][0] == "bad_pair"


def test_complements_min_occurrences(matrix):
    matrix.record_run(["a", "rare"], success=True)  # 1 occurrence
    assert matrix.complements("a") == []  # below MIN_PAIR_OCCURRENCES
    assert matrix.complements("a", min_occurrences=1)[0][0] == "rare"


def test_complements_unknown_tool(matrix):
    matrix.record_run(["a", "b"], success=True)
    assert matrix.complements("ghost") == []


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    m1 = ComplementarityMatrix(home=tmp_path)
    m1.record_run(["a", "b"], success=True)
    m2 = ComplementarityMatrix(home=tmp_path)
    assert m2.pair_stats("a", "b")["occurrences"] == 1


def test_snapshot_shape(matrix):
    matrix.record_run(["a", "b"], success=True)
    snap = matrix.snapshot()
    assert "pairs" in snap
    assert snap["runs"] == 1
