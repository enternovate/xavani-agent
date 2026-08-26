# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

from types import SimpleNamespace
from unittest.mock import patch

import cli as cli_mod
from cli import XavaniCLI


def _make_cli(*, total_tokens=None):
    cli = XavaniCLI.__new__(XavaniCLI)
    cli.tool_progress_mode = "all"
    cli._spinner_text = ""
    cli._tool_start_time = 0.0
    cli._pending_tool_info = {}
    cli._last_scrollback_tool = ""
    cli._active_tool_calls = []
    cli._pending_edit_snapshots = {}
    cli._invalidate = lambda: None
    cli.agent = SimpleNamespace() if total_tokens is None else SimpleNamespace(
        session_total_tokens=total_tokens,
    )
    return cli


def test_tool_started_renders_spinner_tool_name_and_elapsed_time():
    cli = _make_cli()

    with patch.object(cli_mod.time, "monotonic", side_effect=[100.0, 104.2, 104.2]):
        cli._on_tool_progress("tool.started", "terminal", "git status", {"command": "git status"})
        rendered = cli._render_spinner_text()

    assert "git status" in rendered
    assert "4.2s" in rendered
    assert any(frame in rendered for frame in cli_mod._COMMAND_SPINNER_FRAMES)


def test_tool_status_line_includes_session_token_meter_when_available():
    cli = _make_cli(total_tokens=1234)

    with patch.object(cli_mod.time, "monotonic", return_value=100.0):
        cli._on_tool_progress("tool.started", "read_file", "cli.py", {"path": "cli.py"})
        rendered = cli._render_spinner_text()

    assert "tokens" in rendered
    assert "1.2K" in rendered


def test_tool_status_line_omits_token_meter_when_usage_is_unavailable():
    cli = _make_cli()

    with patch.object(cli_mod.time, "monotonic", return_value=100.0):
        cli._on_tool_progress("tool.started", "read_file", "cli.py", {"path": "cli.py"})
        rendered = cli._render_spinner_text()

    assert "tokens" not in rendered


def test_completed_tool_removes_finished_status_line():
    cli = _make_cli()

    with patch.object(cli_mod.time, "monotonic", return_value=100.0):
        cli._on_tool_progress("tool.started", "terminal", "pwd", {"command": "pwd"})
        cli._on_tool_progress(
            "tool.completed",
            "terminal",
            None,
            None,
            duration=0.5,
            is_error=False,
        )

    assert cli._render_spinner_text() == ""
    assert cli._tool_start_time == 0.0


def test_concurrent_tool_completion_keeps_next_tool_status_line():
    cli = _make_cli()

    with patch.object(cli_mod.time, "monotonic", side_effect=[100.0, 101.0, 102.0, 102.0]):
        cli._on_tool_progress("tool.started", "terminal", "pwd", {"command": "pwd"})
        cli._on_tool_progress("tool.started", "read_file", "cli.py", {"path": "cli.py"})
        cli._on_tool_progress(
            "tool.completed",
            "terminal",
            None,
            None,
            duration=1.0,
            is_error=False,
        )
        rendered = cli._render_spinner_text()

    assert "cli.py" in rendered
    assert "pwd" not in rendered


def test_duplicate_concurrent_tool_calls_complete_by_tool_call_id():
    cli = _make_cli()

    with patch.object(cli_mod.time, "monotonic", side_effect=[100.0, 101.0, 102.0, 103.0, 104.0]):
        cli._on_tool_progress(
            "tool.started", "terminal", "pwd", {"command": "pwd"},
            tool_call_id="call-1",
        )
        cli._on_tool_progress(
            "tool.started", "terminal", "git status", {"command": "git status"},
            tool_call_id="call-2",
        )

        cli._on_tool_progress(
            "tool.completed",
            "terminal",
            None,
            None,
            duration=1.0,
            is_error=False,
            tool_call_id="call-2",
        )
        rendered_after_second = cli._render_spinner_text()

        cli._on_tool_progress(
            "tool.completed",
            "terminal",
            None,
            None,
            duration=1.0,
            is_error=False,
            tool_call_id="call-1",
        )
        rendered_after_first = cli._render_spinner_text()

    assert "pwd" in rendered_after_second
    assert "git status" not in rendered_after_second
    assert rendered_after_first == ""
