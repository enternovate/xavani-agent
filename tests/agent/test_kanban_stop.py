"""Tests for the kanban worker terminal-tool stop guard (agent/kanban_stop.py)."""

import os

import pytest

from agent.kanban_stop import (
    _TERMINAL_KANBAN_TOOLS,
    build_kanban_stop_nudge,
    kanban_stop_nudge_enabled,
    session_called_kanban_terminal,
)


@pytest.fixture(autouse=True)
def _clear_kanban_env(monkeypatch):
    monkeypatch.delenv("XAVANI_KANBAN_TASK", raising=False)
    monkeypatch.delenv("XAVANI_KANBAN_STOP_NUDGE", raising=False)


class TestKanbanStopNudgeEnabled:
    def test_disabled_without_task(self):
        assert kanban_stop_nudge_enabled() is False

    def test_enabled_with_task(self, monkeypatch):
        monkeypatch.setenv("XAVANI_KANBAN_TASK", "task-1")
        assert kanban_stop_nudge_enabled() is True

    def test_opt_out_with_task(self, monkeypatch):
        monkeypatch.setenv("XAVANI_KANBAN_TASK", "task-1")
        monkeypatch.setenv("XAVANI_KANBAN_STOP_NUDGE", "false")
        assert kanban_stop_nudge_enabled() is False

    def test_opt_out_variants(self, monkeypatch):
        monkeypatch.setenv("XAVANI_KANBAN_TASK", "task-1")
        for value in ("0", "no", "off", "FALSE"):
            monkeypatch.setenv("XAVANI_KANBAN_STOP_NUDGE", value)
            assert kanban_stop_nudge_enabled() is False


class TestSessionCalledKanbanTerminal:
    def test_empty_messages(self):
        assert session_called_kanban_terminal(None) is False
        assert session_called_kanban_terminal([]) is False

    def test_detects_complete_in_assistant_tool_calls(self):
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "kanban_complete", "arguments": "{}"}}
                ],
            }
        ]
        assert session_called_kanban_terminal(messages) is True

    def test_detects_block_in_tool_role(self):
        messages = [
            {"role": "assistant", "content": "blocking now"},
            {"role": "tool", "name": "kanban_block", "content": "ok"},
        ]
        assert session_called_kanban_terminal(messages) is True

    def test_ignores_other_tools(self):
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": "{}"}}
                ],
            }
        ]
        assert session_called_kanban_terminal(messages) is False

    def test_handles_plain_text_reply(self):
        messages = [{"role": "assistant", "content": "I will write the report now"}]
        assert session_called_kanban_terminal(messages) is False


class TestBuildKanbanStopNudge:
    def test_returns_none_without_task(self):
        assert build_kanban_stop_nudge(messages=[]) is None

    def test_returns_none_when_terminal_called(self, monkeypatch):
        monkeypatch.setenv("XAVANI_KANBAN_TASK", "task-1")
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "kanban_complete", "arguments": "{}"}}
                ],
            }
        ]
        assert build_kanban_stop_nudge(messages=messages) is None

    def test_returns_none_when_attempts_exhausted(self, monkeypatch):
        monkeypatch.setenv("XAVANI_KANBAN_TASK", "task-1")
        nudge = build_kanban_stop_nudge(messages=[], attempts=2, max_attempts=2)
        assert nudge is None

    def test_returns_nudge_for_plain_text_exit(self, monkeypatch):
        monkeypatch.setenv("XAVANI_KANBAN_TASK", "task-42")
        nudge = build_kanban_stop_nudge(messages=[{"role": "assistant", "content": "done"}])
        assert nudge is not None
        assert "task-42" in nudge
        assert "kanban_complete" in nudge
        assert "kanban_block" in nudge

    def test_uses_default_task_label(self, monkeypatch):
        # No task env at all (fixture already cleared it) - the guard is
        # disabled, so the nudge must be None even with empty messages.
        assert build_kanban_stop_nudge(messages=[]) is None

    def test_terminal_tools_constant(self):
        assert _TERMINAL_KANBAN_TOOLS == {"kanban_complete", "kanban_block"}
