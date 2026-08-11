# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for read-only plan mode (backlog D82)."""

import json

import pytest

from tools.registry import ToolRegistry, is_plan_mode, set_plan_mode


@pytest.fixture(autouse=True)
def _plan_mode_off():
    set_plan_mode(False)
    yield
    set_plan_mode(False)


def _register_write_tool(reg: ToolRegistry, name: str = "zz_plan_test_write") -> dict:
    called = {"ran": False}

    def handler(args, **kwargs):
        called["ran"] = True
        return json.dumps({"ok": True})

    reg.register(name, "test", {"type": "object", "properties": {}}, handler)
    return called


def test_blocks_write_tool_in_plan_mode():
    reg = ToolRegistry()
    called = _register_write_tool(reg)
    set_plan_mode(True)

    result = reg.dispatch("zz_plan_test_write", {})

    assert "BLOCKED" in result
    assert "plan mode" in result
    assert called["ran"] is False


def test_allows_read_tool_in_plan_mode():
    reg = ToolRegistry()
    called = {"ran": False}

    def dummy(args, **kwargs):
        called["ran"] = True
        return json.dumps({"ok": True})

    reg.register("read_file", "test", {"type": "object", "properties": {}}, dummy)
    set_plan_mode(True)

    result = reg.dispatch("read_file", {})

    assert "BLOCKED" not in result
    assert called["ran"] is True


def test_off_mode_dispatches_normally():
    reg = ToolRegistry()
    called = _register_write_tool(reg)

    result = reg.dispatch("zz_plan_test_write", {})

    assert "BLOCKED" not in result
    assert called["ran"] is True


def test_plan_mode_state_functions():
    assert is_plan_mode() is False

    set_plan_mode(True)
    assert is_plan_mode() is True

    set_plan_mode(False)
    assert is_plan_mode() is False
