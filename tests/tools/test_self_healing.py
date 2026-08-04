# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G03: self-healing degradation tests."""

import time

import pytest

import tools.self_healing as sh
from tools.self_healing import _HEAL_WINDOW_SECONDS, SelfHealer


@pytest.fixture
def healer():
    return SelfHealer()


# ── planning ───────────────────────────────────────────────────────


def test_plan_healthy_signals_empty(healer):
    actions = healer.plan({"tool_health_ok": {"ok": 10, "total": 10}})
    assert actions == []


def test_plan_degraded_tools(healer):
    actions = healer.plan({"tool_health_ok": {"ok": 2, "total": 10}})
    assert any(a["id"] == "rescan_tools" for a in actions)


def test_plan_cost_burn(healer):
    actions = healer.plan({"cost_burn_exceeded": True})
    assert any(a["id"] == "throttle_outbound" for a in actions)


def test_plan_error_rate(healer):
    actions = healer.plan({"error_rate": 0.9})
    assert any(a["id"] == "flush_error_log" for a in actions)


def test_plan_unknown_signal_ignored(healer):
    assert healer.plan({"mystery": 42}) == []


def test_plan_marks_rate_limited(healer):
    actions = healer.plan({"cost_burn_exceeded": True})
    assert actions[0]["executable"] is True


# ── execution ──────────────────────────────────────────────────────


def test_execute_known_action(healer, monkeypatch):
    monkeypatch.setattr(sh.SelfHealer, "_heal_throttle_outbound", staticmethod(lambda: True))
    assert healer.execute("throttle_outbound") is True
    assert len(healer.history()) == 1


def test_execute_unknown_action(healer):
    assert healer.execute("delete_everything") is False


def test_execute_rate_limited(healer, monkeypatch):
    monkeypatch.setattr(sh.SelfHealer, "_heal_throttle_outbound", staticmethod(lambda: True))
    assert healer.execute("throttle_outbound") is True
    # Second run within the window is refused.
    assert healer.execute("throttle_outbound") is False


def test_rate_limit_expires(healer, monkeypatch):
    monkeypatch.setattr(sh.SelfHealer, "_heal_throttle_outbound", staticmethod(lambda: True))
    healer.execute("throttle_outbound")
    # Force the last-run timestamp into the past.
    healer._last_run["throttle_outbound"] = time.time() - _HEAL_WINDOW_SECONDS - 1
    assert healer.execute("throttle_outbound") is True


def test_history_records_failures(healer, monkeypatch):
    monkeypatch.setattr(sh.SelfHealer, "_heal_flush_error_log", staticmethod(lambda: False))
    assert healer.execute("flush_error_log") is False
    assert healer.history()[-1]["ok"] is False


def test_execute_rescan_tools_safe(healer):
    # The real action must not raise and must not be destructive.
    assert healer.execute("rescan_tools") is True


def test_execute_flush_log_safe(healer, tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "gateway.log").write_text("old", encoding="utf-8")
    assert healer.execute("flush_error_log") is True
    assert (log_dir / "gateway.log.1").exists()


# ── degradation checks ─────────────────────────────────────────────


def test_is_degraded_thresholds():
    assert sh.SelfHealer._is_degraded("tool_health_ok", {"ok": 6, "total": 10}) is True
    assert sh.SelfHealer._is_degraded("tool_health_ok", {"ok": 8, "total": 10}) is False
    assert sh.SelfHealer._is_degraded("cost_burn_exceeded", True) is True
    assert sh.SelfHealer._is_degraded("error_rate", 0.5) is True
    assert sh.SelfHealer._is_degraded("error_rate", 0.1) is False
    assert sh.SelfHealer._is_degraded("mystery", 1) is False
