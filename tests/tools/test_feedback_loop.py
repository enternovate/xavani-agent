# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B13: feedback loop tests."""

import pytest

from tools.feedback_loop import (
    STRUGGLE_THRESHOLD,
    FeedbackLoop,
    VALID_SIGNALS,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def loop(tmp_path):
    return FeedbackLoop(home=tmp_path)


# ── recording ──────────────────────────────────────────────────────


def test_record_accepted_signals(loop):
    assert loop.record("code-review", "up") is True
    assert loop.record("code-review", "down") is True
    assert loop.record("code-review", "retry") is True
    assert loop.event_count() == 3


def test_record_invalid_signal_rejected(loop):
    assert loop.record("code-review", "meh") is False
    assert loop.event_count() == 0


def test_counts_shape(loop):
    loop.record("code-review", "up")
    loop.record("code-review", "up")
    loop.record("code-review", "down")
    counts = loop.counts("code-review")
    assert counts == {"up": 2, "down": 1, "retry": 0}


def test_counts_unknown_task(loop):
    assert loop.counts("ghost") == {"up": 0, "down": 0, "retry": 0}


# ── satisfaction ───────────────────────────────────────────────────


def test_satisfaction_none_without_votes(loop):
    assert loop.satisfaction("code-review") is None


def test_satisfaction_ratio(loop):
    loop.record("code-review", "up")
    loop.record("code-review", "up")
    loop.record("code-review", "down")
    assert loop.satisfaction("code-review") == pytest.approx(2 / 3)


def test_retry_does_not_affect_satisfaction(loop):
    loop.record("code-review", "up")
    loop.record("code-review", "retry")
    loop.record("code-review", "retry")
    assert loop.satisfaction("code-review") == 1.0


def test_trend_shape(loop):
    loop.record("code-review", "down")
    trend = loop.trend("code-review")
    assert trend["task_type"] == "code-review"
    assert trend["satisfaction"] == 0.0
    assert trend["struggling"] is True


def test_not_struggling_when_positive(loop):
    loop.record("code-review", "up")
    assert loop.trend("code-review")["struggling"] is False


def test_struggling_threshold_value():
    assert STRUGGLE_THRESHOLD == 0.4


# ── struggling tasks ───────────────────────────────────────────────


def test_struggling_tasks_detected(loop):
    loop.record("code-review", "down")
    loop.record("docs", "up")
    assert loop.struggling_tasks() == ["code-review"]


def test_no_struggling_when_empty(loop):
    assert loop.struggling_tasks() == []


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    loop1 = FeedbackLoop(home=tmp_path)
    loop1.record("code-review", "up")
    loop2 = FeedbackLoop(home=tmp_path)
    assert loop2.counts("code-review")["up"] == 1


def test_snapshot_shape(loop):
    loop.record("code-review", "up")
    snap = loop.snapshot()
    assert "events" in snap
    assert "by_task" in snap
    assert len(snap["events"]) == 1
