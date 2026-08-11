# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B09: metacognition — confidence calibration tests."""

import pytest

from tools.metacognition import CalibrationTracker

pytestmark = pytest.mark.integration


@pytest.fixture
def tracker(tmp_path):
    return CalibrationTracker(home=tmp_path)


# ── estimate / outcome flow ────────────────────────────────────────


def test_estimate_then_outcome_resolves(tracker):
    assert tracker.record_estimate("t1", 0.9) is True
    assert tracker.pending_count() == 1
    assert tracker.record_outcome("t1", success=True) is True
    assert tracker.pending_count() == 0
    assert tracker.resolved_count() == 1


def test_outcome_without_estimate_rejected(tracker):
    assert tracker.record_outcome("ghost", success=True) is False


def test_invalid_confidence_rejected(tracker):
    assert tracker.record_estimate("t1", -0.1) is False
    assert tracker.record_estimate("t2", 1.5) is False
    assert tracker.pending_count() == 0


def test_duplicate_estimate_overwrites(tracker):
    tracker.record_estimate("t1", 0.5)
    tracker.record_estimate("t1", 0.8)
    tracker.record_outcome("t1", success=True)
    # Only ONE resolved entry — the second estimate won.
    assert tracker.resolved_count() == 1


# ── calibration report ─────────────────────────────────────────────


def test_report_empty(tracker):
    report = tracker.calibration_report()
    assert report["total_resolved"] == 0
    assert report["buckets"] == []
    assert report["overconfident"] == []


def test_report_buckets_confidence(tracker):
    # 5 estimates at 0.9, all successful -> 0.8-1.0 bucket, gap ~ -0.1
    for i in range(5):
        tracker.record_estimate(f"t{i}", 0.9)
        tracker.record_outcome(f"t{i}", success=True)
    report = tracker.calibration_report()
    assert report["total_resolved"] == 5
    assert len(report["buckets"]) == 1
    bucket = report["buckets"][0]
    assert bucket["samples"] == 5
    assert bucket["actual_success_rate"] == 1.0
    assert bucket["mid_confidence"] == pytest.approx(0.905)  # (0.8+1.01)/2
    assert bucket["gap"] == pytest.approx(0.095)


def test_report_overconfident_detected(tracker):
    # Claims 0.9 confidence, fails 80% of the time.
    for i in range(5):
        tracker.record_estimate(f"t{i}", 0.9)
        tracker.record_outcome(f"t{i}", success=False)
    report = tracker.calibration_report()
    assert report["overconfident"]
    assert report["calibrated"] == []


def test_report_underconfident_detected(tracker):
    # Claims 0.1 confidence, succeeds 100% of the time.
    for i in range(5):
        tracker.record_estimate(f"t{i}", 0.1)
        tracker.record_outcome(f"t{i}", success=True)
    report = tracker.calibration_report()
    assert report["underconfident"]


def test_report_min_samples_filters(tracker):
    for i in range(2):  # below min_samples=3
        tracker.record_estimate(f"t{i}", 0.9)
        tracker.record_outcome(f"t{i}", success=True)
    report = tracker.calibration_report(min_samples=3)
    assert report["reported"] == []


def test_report_calibrated_bucket(tracker):
    for i in range(5):
        tracker.record_estimate(f"t{i}", 0.5)
        tracker.record_outcome(f"t{i}", success=True)  # 100% vs 50% -> under
    # Second bucket: 0.5 estimate, 0.6 success rate -> gap 0.1 -> calibrated.
    report = tracker.calibration_report()
    assert any(b["samples"] >= 3 for b in report["buckets"])


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    t1 = CalibrationTracker(home=tmp_path)
    t1.record_estimate("t1", 0.7)
    t2 = CalibrationTracker(home=tmp_path)
    assert t2.pending_count() == 1


def test_snapshot_shape(tracker):
    tracker.record_estimate("t1", 0.8)
    snap = tracker.snapshot()
    assert "pending" in snap
    assert "resolved" in snap
