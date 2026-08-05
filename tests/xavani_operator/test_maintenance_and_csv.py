# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E05/G03: sessions CSV export + idle maintenance tests."""

import os
import time
from pathlib import Path

import pytest

from xavani_cli.session_export_csv import sessions_to_csv
from xavani_operator import maintenance


@pytest.fixture(autouse=True)
def _home(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    return tmp_path


# ── E05 CSV export ────────────────────────────────────────────────────


def test_csv_header_and_rows():
    sessions = [
        {
            "id": "s1",
            "title": "fix tirith",
            "source": "cli",
            "model": "claude-sonnet-4.6",
            "started_at": "2026-08-04T10:00:00",
            "estimated_cost_usd": 0.25,
            "actual_cost_usd": 0.2,
            "cost_status": "estimated",
            "cost_source": "ledger",
        }
    ]
    text = sessions_to_csv(sessions)
    lines = text.strip().splitlines()
    assert "session_id" in lines[0]
    assert "estimated_cost_usd" in lines[0]
    assert lines[1].startswith("s1,")
    assert "0.25" in lines[1]
    assert "fix tirith" in lines[1]


def test_csv_handles_missing_fields():
    text = sessions_to_csv([{"id": "s2"}])
    lines = text.strip().splitlines()
    assert lines[1].startswith("s2,")


# ── G03 maintenance ───────────────────────────────────────────────────


def test_run_maintenance_never_raises(tmp_path):
    result = maintenance.run_maintenance()
    assert "vacuum" in result
    assert "stale_locks" in result
    assert "log_rotation" in result


def test_stale_lock_gc_removes_old_locks(tmp_path):
    home = tmp_path
    stale = home / "gateway.lock"
    stale.write_text("pid", encoding="utf-8")
    old = time.time() - maintenance._STALE_LOCK_AGE_SECONDS - 60
    os.utime(stale, (old, old))
    fresh = home / "fresh.pid"
    fresh.write_text("pid", encoding="utf-8")

    result = maintenance._gc_stale_locks()
    assert "gateway.lock" in result["removed"]
    assert fresh.exists()


def test_gateway_has_active_turns_detects_agents():
    class _Runner:
        pass

    runner = _Runner()
    runner._running_agents = {}
    assert maintenance.gateway_has_active_turns(runner) is False

    runner._running_agents = {"s1": object()}
    assert maintenance.gateway_has_active_turns(runner) is True


def test_vacuum_ok_with_real_db(tmp_path):
    from xavani_state import SessionDB

    db = SessionDB(tmp_path / "state.db")
    db.record_session("s1", "cli", "chat")
    result = maintenance._vacuum_session_db()
    assert result["ok"] is True
