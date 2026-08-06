# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""E02: per-turn timeline trace tests."""

from __future__ import annotations

import pytest

from agent.trajectory import load_turn_timeline, record_turn_timeline, turn_timeline_path


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    monkeypatch.setattr("xavani_constants.get_xavani_home", lambda: tmp_path)


def test_record_and_load_round_trip():
    assert record_turn_timeline({"session_id": "s1", "model": "m", "final": "ok"})
    records = load_turn_timeline()
    assert len(records) == 1
    assert records[0]["session_id"] == "s1"
    assert records[0]["timestamp"]  # defaulted


def test_load_orders_newest_first():
    record_turn_timeline({"n": 1})
    record_turn_timeline({"n": 2})
    assert [r["n"] for r in load_turn_timeline()] == [2, 1]


def test_load_limit():
    for i in range(5):
        record_turn_timeline({"n": i})
    assert len(load_turn_timeline(limit=2)) == 2


def test_record_never_raises_when_logs_dir_blocked(tmp_path):
    (tmp_path / "logs").write_text("not a directory", encoding="utf-8")
    assert record_turn_timeline({"final": "x"}) is False


def test_timeline_path_under_home_logs(tmp_path):
    assert turn_timeline_path() == str(tmp_path / "logs" / "turn_timeline.jsonl")
