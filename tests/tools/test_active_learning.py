# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B03: active learning loop tests."""

import pytest

from tools.active_learning import ActiveLearningLoop, threshold


@pytest.fixture
def loop(tmp_path):
    return ActiveLearningLoop(home=tmp_path)


# ── failure tracking ───────────────────────────────────────────────


def test_record_failure_counts(loop):
    loop.record_failure("code-review", "missed a race condition")
    loop.record_failure("code-review", "missed a race condition")
    assert loop.failure_count("code-review") == 2


def test_failure_types_listed(loop):
    loop.record_failure("code-review")
    loop.record_failure("deploy")
    assert loop.failure_types() == ["code-review", "deploy"]


def test_empty_loop_no_failures(loop):
    assert loop.failure_types() == []
    assert loop.failure_count("anything") == 0


def test_persists_across_instances(tmp_path):
    loop1 = ActiveLearningLoop(home=tmp_path)
    loop1.record_failure("code-review")
    loop2 = ActiveLearningLoop(home=tmp_path)
    assert loop2.failure_count("code-review") == 1


# ── suggestion cycle ───────────────────────────────────────────────


def test_no_suggestion_below_threshold(loop):
    loop.record_failure("x")
    loop.record_failure("x")
    assert loop.suggest_skill("x") is None


def test_suggestion_after_threshold(loop):
    for _ in range(threshold()):
        loop.record_failure("code-review", "missed bug")
    suggestion = loop.suggest_skill("code-review")
    assert suggestion is not None
    assert suggestion["task_type"] == "code-review"
    assert suggestion["status"] == "suggested"
    assert suggestion["failure_count"] == threshold()


def test_no_duplicate_suggestion(loop):
    for _ in range(threshold()):
        loop.record_failure("x")
    first = loop.suggest_skill("x")
    assert first is not None
    assert loop.suggest_skill("x") is None  # already suggested


def test_validate_merged(loop):
    for _ in range(threshold()):
        loop.record_failure("x")
    suggestion = loop.suggest_skill("x")
    assert loop.validate_suggestion(suggestion["id"], passed=True) is True
    assert suggestion["status"] == "merged"
    assert len(loop.merged_suggestions()) == 1
    assert loop.pending_suggestions() == []


def test_validate_rejected(loop):
    for _ in range(threshold()):
        loop.record_failure("x")
    suggestion = loop.suggest_skill("x")
    assert loop.validate_suggestion(suggestion["id"], passed=False) is True
    assert suggestion["status"] == "rejected"
    assert loop.merged_suggestions() == []


def test_validate_unknown_id(loop):
    assert loop.validate_suggestion("ghost", passed=True) is False


def test_suggestion_errors_captured(loop):
    for i in range(threshold()):
        loop.record_failure("x", f"error {i}")
    suggestion = loop.suggest_skill("x")
    assert any("error" in e for e in suggestion["errors"])


# ── snapshot ───────────────────────────────────────────────────────


def test_snapshot_shape(loop):
    loop.record_failure("x")
    snap = loop.snapshot()
    assert "failures" in snap
    assert "suggestions" in snap
