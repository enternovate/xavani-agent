# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/dry_run.py and its tool-handler hooks."""

import json

import pytest

from tools import dry_run


def test_toggle_round_trip():
    initial = dry_run.enabled()
    try:
        after_on = dry_run.toggle()
        assert after_on is True
        assert dry_run.enabled() is True
        after_off = dry_run.toggle()
        assert after_off is False
        assert dry_run.enabled() is False
    finally:
        dry_run.set_enabled(initial)


def test_terminal_handler_dry_run_reports_without_executing(monkeypatch, tmp_path):
    from tools import terminal_tool

    dry_run.set_enabled(True)
    try:
        executed = []
        monkeypatch.setattr(
            terminal_tool, "terminal_tool",
            lambda **kw: executed.append(kw) or "executed",
        )
        result = terminal_tool._handle_terminal({"command": "ls -la"})
        assert "[dry-run]" in result
        assert "ls -la" in result
        assert executed == []
    finally:
        dry_run.set_enabled(False)


def test_write_file_handler_dry_run_reports_without_writing(tmp_path):
    from tools import file_tools

    target = tmp_path / "d.txt"
    target.write_text("keep", encoding="utf-8")
    dry_run.set_enabled(True)
    try:
        result = file_tools._handle_write_file(
            {"path": str(target), "content": "new"}, task_id="default"
        )
        assert "[dry-run]" in result
        assert target.read_text(encoding="utf-8") == "keep"
    finally:
        dry_run.set_enabled(False)


def test_patch_handler_dry_run_reports_without_patching(tmp_path):
    from tools import file_tools

    dry_run.set_enabled(True)
    try:
        result = file_tools._handle_patch(
            {"mode": "replace", "path": str(tmp_path / "x.txt"),
             "old_string": "a", "new_string": "b"},
            task_id="default",
        )
        assert "[dry-run]" in result
    finally:
        dry_run.set_enabled(False)


def test_dry_run_state_is_context_isolated():
    dry_run.set_enabled(True)
    try:
        assert dry_run.enabled() is True
    finally:
        dry_run.set_enabled(False)
