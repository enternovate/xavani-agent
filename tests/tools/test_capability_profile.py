# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B07: model capability self-assessment tests."""

import pytest

from tools.capability_profile import MIN_OUTCOMES, CapabilityTracker

pytestmark = pytest.mark.integration


@pytest.fixture
def tracker(tmp_path):
    return CapabilityTracker(home=tmp_path)


# ── recording ──────────────────────────────────────────────────────


def test_record_outcome_counts( tracker):
    tracker.record_outcome("model-a", "code-review", success=True)
    tracker.record_outcome("model-a", "code-review", success=False)
    stats = tracker.task_stats("model-a", "code-review")
    assert stats["total"] == 2
    assert stats["success"] == 1
    assert stats["success_rate"] == 0.5


def test_record_unknown_model_task( tracker):
    stats = tracker.task_stats("ghost", "anything")
    assert stats["total"] == 0
    assert stats["success_rate"] is None


def test_task_stats_empty_model( tracker):
    tracker.record_outcome("model-a", "task-1", success=True)
    stats = tracker.task_stats("model-a", "task-2")
    assert stats["success_rate"] is None


# ── profiles ───────────────────────────────────────────────────────


def test_profile_excludes_under_sampled( tracker):
    tracker.record_outcome("model-a", "task-x", success=True)  # 1 outcome
    profile = tracker.profile("model-a")
    assert "task-x" not in profile["tasks"]
    assert profile["strengths"] == []


def test_profile_strengths_ranked( tracker):
    for _ in range(MIN_OUTCOMES):
        tracker.record_outcome("model-a", "weak-task", success=False)
    for _ in range(MIN_OUTCOMES):
        tracker.record_outcome("model-a", "strong-task", success=True)
    profile = tracker.profile("model-a")
    assert profile["strengths"][0] == "strong-task"
    assert profile["tasks"]["strong-task"]["success_rate"] == 1.0
    assert profile["tasks"]["weak-task"]["success_rate"] == 0.0


def test_profile_evidence_total( tracker):
    tracker.record_outcome("model-a", "t1", success=True)
    tracker.record_outcome("model-a", "t2", success=False)
    assert tracker.profile("model-a")["evidence_total"] == 2


def test_profile_unknown_model( tracker):
    profile = tracker.profile("ghost")
    assert profile["tasks"] == {}
    assert profile["evidence_total"] == 0


# ── best_for ───────────────────────────────────────────────────────


def test_best_for_picks_highest_rate( tracker):
    for _ in range(MIN_OUTCOMES):
        tracker.record_outcome("slow-model", "code-review", success=False)
    for _ in range(MIN_OUTCOMES):
        tracker.record_outcome("fast-model", "code-review", success=True)
    assert tracker.best_for("code-review") == "fast-model"


def test_best_for_none_without_evidence( tracker):
    assert tracker.best_for("code-review") is None


def test_best_for_ignores_under_sampled( tracker):
    tracker.record_outcome("lucky-model", "code-review", success=True)  # 1 outcome
    assert tracker.best_for("code-review") is None


def test_best_for_min_total_parameter( tracker):
    for _ in range(3):
        tracker.record_outcome("m", "t", success=True)
    assert tracker.best_for("t", min_total=5) is None
    assert tracker.best_for("t", min_total=2) == "m"


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    t1 = CapabilityTracker(home=tmp_path)
    t1.record_outcome("model-a", "code-review", success=True)
    t2 = CapabilityTracker(home=tmp_path)
    assert t2.task_stats("model-a", "code-review")["total"] == 1


def test_models_list( tracker):
    tracker.record_outcome("model-b", "t", success=True)
    tracker.record_outcome("model-a", "t", success=True)
    assert tracker.models() == ["model-a", "model-b"]


def test_snapshot_shape( tracker):
    tracker.record_outcome("model-a", "t", success=True)
    snap = tracker.snapshot()
    assert "models" in snap
    assert "model-a" in snap["models"]
