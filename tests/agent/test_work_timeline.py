# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R2 Task 22 — the local work timeline.

Proves: events land beside the session log; secrets/headers/environments and
long contents never do; unparseable lines skip; the metric hook records
tool.started + tool.completed; the selector records skill.loaded; and a
replay executes zero tools.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent import work_timeline as wt


class _FakeAgent:
    """Session-shaped host surface for timeline tests."""

    def __init__(self, tmp_path: Path):
        sessions = tmp_path / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        self.session_log_file = sessions / "session_run_test.json"
        self.session_id = "test"


def _events(agent):
    path = wt.timeline_path(agent)
    assert path is not None
    return wt.read_timeline(path)


def test_unknown_event_type_is_rejected(tmp_path):
    agent = _FakeAgent(tmp_path)
    with pytest.raises(ValueError):
        wt.record_event(agent, "not.a.type", x=1)


def test_events_are_written_beside_the_session_log(tmp_path):
    agent = _FakeAgent(tmp_path)
    record = wt.record_event(agent, "task.started", summary="do the thing")
    assert record is not None
    path = wt.timeline_path(agent)
    assert path is not None
    assert path.name == "session_run_test.timeline.jsonl"
    assert path.parent == agent.session_log_file.parent
    events = _events(agent)
    assert events and events[0]["type"] == "task.started"
    assert isinstance(events[0]["ts"], float)


def test_sanitizer_drops_secrets_and_truncates(tmp_path):
    agent = _FakeAgent(tmp_path)
    wt.record_event(
        agent,
        "tool.completed",
        tool="terminal",
        api_key="sk-secret",
        authorization="Bearer xyz",
        TOKEN="t0ken",
        env={"PATH": "/usr/bin"},
        reasoning="deep thought",
        output="x" * 500,
        ok=True,
        duration=1.25,
    )
    event = _events(agent)[0]
    assert "api_key" not in event
    assert "authorization" not in event
    assert "token" not in event
    assert "env" not in event
    assert "reasoning" not in event
    assert event["ok"] is True
    assert event["duration"] == 1.25
    assert len(event["output"]) <= wt._MAX_VALUE_LEN + 1
    assert event["output"].endswith("…")


def test_read_timeline_skips_unparseable_lines(tmp_path):
    agent = _FakeAgent(tmp_path)
    path = wt.timeline_path(agent)
    assert path is not None
    path.write_text(
        json.dumps({"ts": 1.0, "type": "task.started"}) + "\n"
        + "not json at all\n"
        + "\n"
        + json.dumps({"ts": 2.0, "type": "task.completed"}) + "\n",
        encoding="utf-8",
    )
    events = wt.read_timeline(path)
    assert [e["type"] for e in events] == ["task.started", "task.completed"]


def test_replay_executes_zero_tools(tmp_path):
    agent = _FakeAgent(tmp_path)
    wt.record_event(agent, "tool.started", tool="write_file")
    wt.record_event(agent, "tool.completed", tool="write_file", duration=0.1)
    events = _events(agent)

    with (
        patch("agent.tool_executor.execute_tool_calls_sequential") as seq,
        patch("agent.tool_executor.execute_tool_calls_concurrent") as conc,
    ):
        replayed = wt.replay(events)

    seq.assert_not_called()
    conc.assert_not_called()
    assert replayed == events
    # Copies, not references: mutating a replayed event cannot alter the file.
    replayed[0]["type"] = "tampered"
    assert _events(agent)[0]["type"] == "tool.started"


def test_metric_hook_records_started_and_completed(tmp_path):
    from agent.tool_executor import _record_tool_metric

    agent = _FakeAgent(tmp_path)
    with patch("agent.tool_metrics.record_call"):
        _record_tool_metric(agent, "write_file", started_at=100.0, duration=0.5, is_error=False)

    events = _events(agent)
    kinds = [e["type"] for e in events]
    assert kinds == ["tool.started", "tool.completed"]
    assert events[0]["tool"] == "write_file"
    assert events[0]["at"] == 100.0
    assert events[1]["duration"] == 0.5
    assert events[1]["error"] is False


def test_selector_records_skill_loaded(tmp_path):
    from agent import skill_commands

    agent = _FakeAgent(tmp_path)
    stub_selection = MagicMock()
    stub_selection.skills = ("a", "b")
    stub_selection.consequential = False
    stub_selection.blocked = False
    with (
        patch("agent.workflow_skills.select_workflow", return_value=stub_selection),
        patch.object(skill_commands, "build_workflow_skill_message", return_value="msg"),
        patch("agent.workflow_skills.record_selection", return_value=()),
    ):
        skill_commands.select_workflow_for_agent(agent, "finance", mode="ask")

    events = _events(agent)
    assert len(events) == 1
    assert events[0]["type"] == "skill.loaded"
    assert events[0]["workflow"] == "finance"
    assert events[0]["skills"] == 2
