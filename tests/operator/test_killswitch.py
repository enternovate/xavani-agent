# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the operator kill-switch + the daemon honouring it (v1.0.0 ③ / safety)."""

from __future__ import annotations

from xavani_operator import daemon, killswitch


def test_pause_resume_roundtrip(tmp_path) -> None:
    flag = tmp_path / "PAUSED"
    assert killswitch.is_paused(path=flag) is False
    assert killswitch.resume(path=flag) is False  # nothing to resume

    killswitch.pause("maintenance window", path=flag, now=123.0)
    assert killswitch.is_paused(path=flag) is True
    assert killswitch.pause_reason(path=flag) == "maintenance window"

    assert killswitch.resume(path=flag) is True
    assert killswitch.is_paused(path=flag) is False
    assert killswitch.pause_reason(path=flag) is None


def test_daemon_skips_work_while_paused(tmp_path) -> None:
    hb = tmp_path / "hb.json"
    worked = {"n": 0}

    def tick() -> dict:
        worked["n"] += 1
        return {"acted": True}

    # Paused for the first 2 ticks, then live.
    state = {"i": 0}

    def paused() -> bool:
        state["i"] += 1
        return state["i"] <= 2

    summary = daemon.serve(
        tick,
        interval=0,
        max_iters=4,
        clock=lambda: 1.0,
        sleep=lambda _s: None,
        paused=paused,
        heartbeat=hb,
    )
    assert summary["iters"] == 4
    assert summary["paused"] == 2
    assert summary["acted"] == 2  # only the 2 live ticks did work
    assert worked["n"] == 2  # tick() was never called while paused
    assert daemon.read_status(hb)["status"] == "stopped"


def test_daemon_backward_compatible_without_paused(tmp_path) -> None:
    # Existing callers that don't pass `paused` keep the old behaviour.
    hb = tmp_path / "hb.json"
    summary = daemon.serve(
        lambda: {"acted": True},
        interval=0,
        max_iters=3,
        clock=lambda: 0.0,
        sleep=lambda _s: None,
        heartbeat=hb,
    )
    assert summary == {"iters": 3, "acted": 3, "idle": 0, "paused": 0, "last_status": "working"}
