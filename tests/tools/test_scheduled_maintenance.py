# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G05: scheduled maintenance tests."""

import pytest

from tools.scheduled_maintenance import MaintenancePlanner


@pytest.fixture
def planner(tmp_path):
    return MaintenancePlanner(home=tmp_path)


# ── planning ───────────────────────────────────────────────────────


def test_plan_accepts_valid(planner):
    assert planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly") is True
    assert "prune" in planner.tasks()


def test_plan_rejects_bad_repeat(planner):
    assert planner.plan("prune", "2026-08-10T03:00:00", repeat="hourly") is False


def test_plan_rejects_bad_time(planner):
    assert planner.plan("prune", "not-a-date", repeat="weekly") is False


def test_plan_payload_stored(planner):
    planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly", payload={"max_age_days": 30})
    assert planner.tasks()["prune"]["payload"] == {"max_age_days": 30}


# ── due / completion ───────────────────────────────────────────────


def test_due_before_time_empty(planner):
    planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly")
    assert planner.due(now="2026-08-10T02:59:59") == []


def test_due_at_time(planner):
    planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly")
    due = planner.due(now="2026-08-10T03:00:00")
    assert len(due) == 1
    assert due[0]["task_id"] == "prune"


def test_due_sorted(planner):
    planner.plan("later", "2026-08-10T04:00:00", repeat="weekly")
    planner.plan("earlier", "2026-08-10T03:00:00", repeat="weekly")
    due = planner.due(now="2026-08-10T05:00:00")
    assert [t["task_id"] for t in due] == ["earlier", "later"]


def test_complete_advances_weekly(planner):
    planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly")
    assert planner.complete("prune", now="2026-08-10T03:00:00") is True
    record = planner.tasks()["prune"]
    assert record["next"] == "2026-08-17T03:00:00"
    assert record["last_completed"] == "2026-08-10T03:00:00"
    assert len(planner.history()) == 1


def test_complete_unknown(planner):
    assert planner.complete("ghost") is False


def test_not_due_again_until_next(planner):
    planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly")
    planner.complete("prune", now="2026-08-10T03:00:00")
    assert planner.due(now="2026-08-10T04:00:00") == []
    assert len(planner.due(now="2026-08-17T03:00:00")) == 1


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    p1 = MaintenancePlanner(home=tmp_path)
    p1.plan("prune", "2026-08-10T03:00:00", repeat="weekly")
    p2 = MaintenancePlanner(home=tmp_path)
    assert "prune" in p2.tasks()


def test_snapshot_shape(planner):
    planner.plan("prune", "2026-08-10T03:00:00", repeat="weekly")
    snap = planner.snapshot()
    assert "tasks" in snap
    assert "history" in snap
