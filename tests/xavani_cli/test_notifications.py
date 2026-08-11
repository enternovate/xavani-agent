# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli.notifications (G07 smart notifications)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from xavani_cli import notifications
from xavani_constants import get_xavani_home

pytestmark = pytest.mark.unit


class TestSmartNotify:
    def test_prints_to_console_always(self, capsys):
        notifications.smart_notify("Test", "hello body", level="info")
        out = capsys.readouterr().out
        assert "[info] Test: hello body" in out

    def test_respects_level_in_console_line(self, capsys):
        notifications.smart_notify("Task", "done", level="warning")
        assert "[warning] Task: done" in capsys.readouterr().out

    def test_writes_gateway_log_when_gateway_running(self, monkeypatch, capsys):
        monkeypatch.setenv("XAVANI_GATEWAY_RUNNING", "1")
        notifications.smart_notify("Task", "completed", level="info")
        capsys.readouterr()  # console line already asserted elsewhere
        log_path = get_xavani_home() / "logs" / "gateway.log"
        assert log_path.is_file()
        content = log_path.read_text(encoding="utf-8")
        assert "[info] Task: completed" in content

    def test_no_gateway_log_when_not_running(self, monkeypatch, capsys):
        monkeypatch.delenv("XAVANI_GATEWAY_RUNNING", raising=False)
        notifications.smart_notify("Task", "completed", level="info")
        capsys.readouterr()
        assert not (get_xavani_home() / "logs" / "gateway.log").exists()

    def test_gateway_running_flag(self, monkeypatch):
        monkeypatch.delenv("XAVANI_GATEWAY_RUNNING", raising=False)
        assert notifications.gateway_running() is False
        monkeypatch.setenv("XAVANI_GATEWAY_RUNNING", "0")
        assert notifications.gateway_running() is False
        monkeypatch.setenv("XAVANI_GATEWAY_RUNNING", "1")
        assert notifications.gateway_running() is True

    def test_log_write_failure_is_swallowed(self, monkeypatch, capsys):
        """A failing gateway log append must never raise or skip the console."""
        monkeypatch.setenv("XAVANI_GATEWAY_RUNNING", "1")
        # /dev/null is a file — mkdir under it raises OSError on all platforms
        monkeypatch.setattr(
            notifications,
            "_gateway_log_path",
            lambda: Path("/dev/null") / "not-a-dir" / "gateway.log",
        )
        notifications.smart_notify("Task", "still ok", level="info")
        out = capsys.readouterr().out
        assert "[info] Task: still ok" in out
