# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from types import SimpleNamespace

import pytest

from xavani_cli import agent_hub


@pytest.fixture(autouse=True)
def _clear_parked():
    import xavani_cli.agent_hub as hub

    hub._parked.clear()
    yield
    hub._parked.clear()


@pytest.fixture
def fake_registry(monkeypatch):
    """One running child in the delegate registry."""
    child = SimpleNamespace(steer=lambda text: True)
    record = {
        "subagent_id": "sub-1",
        "parent_id": None,
        "depth": 0,
        "goal": "write the report",
        "model": "test-model",
        "started_at": 0.0,
        "status": "running",
        "tool_count": 2,
        "agent": child,
    }
    import tools.delegate_tool as dt

    monkeypatch.setattr(dt, "_active_subagents", {"sub-1": record})
    lock = __import__("threading").Lock()
    monkeypatch.setattr(dt, "_active_subagents_lock", lock)
    return dt, record


class TestRoster:
    def test_lists_children_with_duration_no_agent_ref(self, fake_registry):
        rows = agent_hub.roster()
        assert len(rows) == 1
        assert rows[0]["subagent_id"] == "sub-1"
        assert "agent" not in rows[0]
        assert "duration_s" in rows[0]


class TestSteer:
    def test_steers_running_child(self, fake_registry):
        assert agent_hub.steer("sub-1", "focus on section 2") is True

    def test_unknown_child_fails(self, fake_registry):
        assert agent_hub.steer("missing", "hello") is False

    def test_empty_text_fails(self, fake_registry):
        assert agent_hub.steer("sub-1", "   ") is False


class TestKill:
    def test_kill_interrupts_and_parks_goal(self, fake_registry, monkeypatch):
        dt, _record = fake_registry
        monkeypatch.setattr(dt, "interrupt_subagent", lambda sid: sid == "sub-1")
        result = agent_hub.kill("sub-1")
        assert result == {"ok": True, "subagent_id": "sub-1"}
        parked = agent_hub.parked()
        assert len(parked) == 1
        assert parked[0]["goal"] == "write the report"

    def test_kill_unknown_child_does_not_park(self, fake_registry, monkeypatch):
        dt, _record = fake_registry
        monkeypatch.setattr(dt, "interrupt_subagent", lambda sid: False)
        result = agent_hub.kill("missing")
        assert result["ok"] is False
        assert agent_hub.parked() == []


class TestRevive:
    def test_revive_spawns_with_parked_goal(self, fake_registry, monkeypatch):
        dt, _record = fake_registry
        monkeypatch.setattr(dt, "interrupt_subagent", lambda sid: True)
        agent_hub.kill("sub-1")
        seen = {}

        def fake_delegate(goal=None, parent_agent=None, **kwargs):
            seen["goal"] = goal
            seen["parent"] = parent_agent
            return '{"results": []}'

        monkeypatch.setattr(dt, "delegate_task", fake_delegate)
        parent = SimpleNamespace()
        result = agent_hub.revive("sub-1", parent)
        assert result["ok"] is True
        assert seen["goal"] == "write the report"
        assert seen["parent"] is parent
        assert agent_hub.parked() == []

    def test_revive_unknown_park_fails(self, fake_registry):
        result = agent_hub.revive("missing", SimpleNamespace())
        assert result["ok"] is False

    def test_revive_restores_park_on_spawn_failure(
        self, fake_registry, monkeypatch
    ):
        dt, _record = fake_registry
        monkeypatch.setattr(dt, "interrupt_subagent", lambda sid: True)
        agent_hub.kill("sub-1")

        def boom(**kwargs):
            raise RuntimeError("spawn failed")

        monkeypatch.setattr(dt, "delegate_task", boom)
        result = agent_hub.revive("sub-1", SimpleNamespace())
        assert result["ok"] is False
        assert len(agent_hub.parked()) == 1
