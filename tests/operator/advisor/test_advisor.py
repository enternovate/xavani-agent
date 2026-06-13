# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Always-On Companion: rituals, schedule, daemon (v1.0.0 ③)."""

from __future__ import annotations

from xavani_operator import daemon
from xavani_operator.advisor import rituals, schedule


# --------------------------------------------------------------------------- #
# Rituals — the 8pm error log
# --------------------------------------------------------------------------- #
def test_evening_prompt_is_an_error_log_not_a_diary() -> None:
    text = rituals.render_evening_prompt()
    assert "predict" in text.lower()
    assert "believe" in text.lower()
    assert "assumption" in text.lower()
    assert "tomorrow" in text.lower()
    assert "diary" in text.lower()  # explicitly framed as NOT a diary


def test_error_log_roundtrip(tmp_path) -> None:
    path = tmp_path / "error_log.jsonl"
    e1 = rituals.ErrorLogEntry(
        date="2026-06-11",
        predictions_missed=[{"predicted": "ship by noon", "actual": "shipped at 4pm"}],
        wasted_effort=[{"assumption": "the API was stable", "cost": "2 hours"}],
        tomorrow_plan=[{"task": "wire the dashboard", "why": "demo", "est": "3h"}],
    )
    rituals.save_error_log(e1, path)
    rituals.save_error_log(rituals.ErrorLogEntry(date="2026-06-12"), path)

    loaded = rituals.load_error_log(path)
    assert len(loaded) == 2
    assert loaded[0].date == "2026-06-11"
    assert loaded[0].wasted_effort[0]["assumption"] == "the API was stable"
    assert loaded[0].tomorrow_plan[0]["task"] == "wire the dashboard"


def test_error_log_entry_autofills_date() -> None:
    e = rituals.ErrorLogEntry(created_at=0.0)  # epoch 0
    assert e.date  # filled from created_at, not blank


def test_render_brief_is_deterministic_and_grounded() -> None:
    kwargs = dict(
        date="2026-06-11",
        perceptions=["3 failing tests on main"],
        goals=["ship v1.0.0"],
        quantum_decision="ship-the-feature",
        wisdom_verdict="reversible, low risk — proceed",
        recommendations=["fix the parser test first"],
    )
    a = rituals.render_brief(**kwargs)
    b = rituals.render_brief(**kwargs)
    assert a == b
    assert "ship v1.0.0" in a and "ship-the-feature" in a and "fix the parser test first" in a


def test_render_brief_quiet_day() -> None:
    assert "Quiet day" in rituals.render_brief(date="2026-06-11")


def test_hourly_nudge() -> None:
    assert rituals.render_hourly_nudge([]) is None
    msg = rituals.render_hourly_nudge(["wire dashboard", "write tests"])
    assert "wire dashboard" in msg and "write tests" in msg


def test_deliver_uses_injected_sender() -> None:
    sent: list[str] = []
    assert rituals.deliver("hello", sent.append) is True
    assert sent == ["hello"]
    assert rituals.deliver(None, sent.append) is False  # nothing to send
    assert rituals.deliver("x", None) is False  # no sender


# --------------------------------------------------------------------------- #
# Schedule
# --------------------------------------------------------------------------- #
def test_advisor_jobs_specs() -> None:
    jobs = {j.name: j for j in schedule.advisor_jobs()}
    assert jobs["xavani.advisor.evening"].schedule == "0 20 * * *"  # 8pm
    assert jobs["xavani.advisor.morning_brief"].schedule == "0 8 * * *"
    assert jobs["xavani.advisor.hourly_chase"].schedule == "0 9-21 * * *"


def test_register_advisor_jobs_with_fake_create() -> None:
    created: list[dict] = []

    def fake_create_job(*, prompt, schedule, name, deliver):  # noqa: A002
        rec = {"prompt": prompt, "schedule": schedule, "name": name, "deliver": deliver}
        created.append(rec)
        return rec

    out = schedule.register_advisor_jobs(deliver="telegram", create_job=fake_create_job)
    assert len(out) == 3
    assert {r["name"] for r in created} == {
        "xavani.advisor.morning_brief",
        "xavani.advisor.hourly_chase",
        "xavani.advisor.evening",
    }
    assert all(r["deliver"] == "telegram" for r in created)


# --------------------------------------------------------------------------- #
# Daemon — 24/7, active only when working
# --------------------------------------------------------------------------- #
def test_daemon_serve_heartbeats_and_counts(tmp_path) -> None:
    hb = tmp_path / "hb.json"
    n = {"i": 0}

    def tick() -> dict:
        n["i"] += 1
        return {"acted": n["i"] % 2 == 0, "note": f"tick {n['i']}"}  # acts on even ticks

    summary = daemon.serve(
        tick, interval=0, max_iters=4, clock=lambda: 123.0, sleep=lambda _s: None, heartbeat=hb
    )
    assert summary["iters"] == 4
    assert summary["acted"] == 2  # ticks 2 and 4
    assert summary["idle"] == 2

    status = daemon.read_status(hb)
    assert status["status"] == "stopped"
    assert status["cycle_count"] == 4
    assert status["last_tick"] == 123.0


def test_daemon_stop_predicate(tmp_path) -> None:
    hb = tmp_path / "hb.json"
    calls = {"i": 0}

    def tick() -> dict:
        calls["i"] += 1
        return {"acted": True}

    # Stop after the first tick.
    summary = daemon.serve(
        tick,
        interval=0,
        max_iters=10,
        clock=lambda: 1.0,
        sleep=lambda _s: None,
        stop=lambda: calls["i"] >= 1,
        heartbeat=hb,
    )
    assert summary["iters"] == 1


def test_read_status_absent(tmp_path) -> None:
    assert daemon.read_status(tmp_path / "nope.json") == {}
