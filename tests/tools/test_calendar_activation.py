# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B15: calendar activation tests."""

import pytest

from tools.calendar_activation import (
    CalendarScheduler,
    _next_occurrence,
    _parse_iso,
)


@pytest.fixture
def scheduler(tmp_path):
    return CalendarScheduler(home=tmp_path)


# ── parsing ────────────────────────────────────────────────────────


def test_parse_iso_variants():
    assert _parse_iso("2026-08-04T09:00:00") is not None
    assert _parse_iso("2026-08-04T09:00") is not None
    assert _parse_iso("2026-08-04") is not None
    assert _parse_iso("not-a-date") is None


def test_next_occurrence_daily():
    base = _parse_iso("2026-08-04T09:00:00")
    assert base is not None
    assert _next_occurrence(base, "daily").isoformat().startswith("2026-08-05T09:00")


def test_next_occurrence_weekly():
    base = _parse_iso("2026-08-04T09:00:00")
    assert base is not None
    assert _next_occurrence(base, "weekly").isoformat().startswith("2026-08-11T09:00")


def test_next_occurrence_monthly():
    base = _parse_iso("2026-08-04T09:00:00")
    assert base is not None
    assert _next_occurrence(base, "monthly").isoformat().startswith("2026-09-04T09:00")


def test_next_occurrence_monthly_year_rollover():
    base = _parse_iso("2026-12-15T10:00:00")
    assert base is not None
    assert _next_occurrence(base, "monthly").isoformat().startswith("2027-01-15T10:00")


# ── scheduling ─────────────────────────────────────────────────────


def test_schedule_accepts_valid(scheduler):
    assert scheduler.schedule("t1", "2026-08-04T09:00:00", repeat="once") is True
    assert "t1" in scheduler.tasks()


def test_schedule_rejects_bad_time(scheduler):
    assert scheduler.schedule("t1", "not-a-time") is False


def test_schedule_rejects_bad_repeat(scheduler):
    assert scheduler.schedule("t1", "2026-08-04T09:00:00", repeat="hourly") is False


def test_schedule_accepts_payload(scheduler):
    scheduler.schedule("t1", "2026-08-04T09:00:00", payload={"report": "daily"})
    assert scheduler.tasks()["t1"]["payload"] == {"report": "daily"}


# ── due / activation ───────────────────────────────────────────────


def test_due_at_exact_time(scheduler):
    scheduler.schedule("t1", "2026-08-04T09:00:00")
    assert len(scheduler.due(now="2026-08-04T09:00:00")) == 1
    assert len(scheduler.due(now="2026-08-04T08:59:59")) == 0


def test_due_sorted_by_time(scheduler):
    scheduler.schedule("late", "2026-08-04T10:00:00")
    scheduler.schedule("early", "2026-08-04T09:00:00")
    due = scheduler.due(now="2026-08-04T11:00:00")
    assert [t["task_id"] for t in due] == ["early", "late"]


def test_once_removed_after_activation(scheduler):
    scheduler.schedule("t1", "2026-08-04T09:00:00")
    assert scheduler.mark_activated("t1", now="2026-08-04T09:00:00") is True
    assert "t1" not in scheduler.tasks()


def test_daily_advances(scheduler):
    scheduler.schedule("t1", "2026-08-04T09:00:00", repeat="daily")
    scheduler.mark_activated("t1", now="2026-08-04T09:00:00")
    assert scheduler.tasks()["t1"]["activated_count"] == 1
    # Not due again until tomorrow.
    assert len(scheduler.due(now="2026-08-04T09:30:00")) == 0
    assert len(scheduler.due(now="2026-08-05T09:00:00")) == 1


def test_mark_unknown_task(scheduler):
    assert scheduler.mark_activated("ghost") is False


def test_cancel(scheduler):
    scheduler.schedule("t1", "2026-08-04T09:00:00")
    assert scheduler.cancel("t1") is True
    assert scheduler.cancel("t1") is False
    assert "t1" not in scheduler.tasks()


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    s1 = CalendarScheduler(home=tmp_path)
    s1.schedule("t1", "2026-08-04T09:00:00")
    s2 = CalendarScheduler(home=tmp_path)
    assert "t1" in s2.tasks()


def test_snapshot_shape(scheduler):
    scheduler.schedule("t1", "2026-08-04T09:00:00")
    snap = scheduler.snapshot()
    assert "tasks" in snap
