# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C07: tool auto-discovery tests."""

import pytest

from tools.auto_discovery import (
    DiscoveryRecord,
    _load_declarative,
    _validate_manifest,
    discover_all_tools,
    load_user_tools,
    user_tools_dir,
)
from tools.registry import ToolRegistry


@pytest.fixture
def registry():
    return ToolRegistry()


def _write_tool(home, name, content):
    tools_dir = home / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    path = tools_dir / f"{name}.yaml"
    path.write_text(content, encoding="utf-8")
    return path


# ── manifest validation ─────────────────────────────────────────────


def test_validate_ok():
    assert _validate_manifest(
        {"name": "greet", "description": "Say hi", "command": "echo hi"},
        __import__("pathlib").Path("/x"),
    ) == ""


def test_validate_missing_keys():
    err = _validate_manifest({"name": "greet"}, __import__("pathlib").Path("/x"))
    assert "missing required key" in err


def test_validate_bad_name():
    err = _validate_manifest(
        {"name": "bad name", "description": "x", "command": "echo"},
        __import__("pathlib").Path("/x"),
    )
    assert "invalid tool name" in err


# ── declarative loading ────────────────────────────────────────────


def test_load_valid_tool(registry, tmp_path):
    _write_tool(tmp_path, "greet", (
        "name: greet\n"
        "description: Say hello\n"
        "command: echo hello\n"
    ))
    records = load_user_tools(registry, home=tmp_path)
    assert len(records) == 1
    assert records[0].ok is True
    assert records[0].source == "user-yaml"
    assert registry.get_entry("greet") is not None


def test_load_bad_tool_reports_error_not_raise(registry, tmp_path):
    _write_tool(tmp_path, "broken", "name: broken\n")  # missing command
    records = load_user_tools(registry, home=tmp_path)
    assert len(records) == 1
    assert records[0].ok is False
    assert records[0].error
    # Bad tools never crash startup.
    assert registry.get_entry("broken") is None


def test_load_empty_dir(registry, tmp_path):
    assert load_user_tools(registry, home=tmp_path) == []


def test_declarative_handler_runs_command(registry, tmp_path):
    _write_tool(tmp_path, "greet", (
        "name: greet\n"
        "description: Say hello\n"
        "command: echo hello\n"
    ))
    load_user_tools(registry, home=tmp_path)
    entry = registry.get_entry("greet")
    assert entry is not None
    result = entry.handler({"args": "world"})
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


def test_declarative_handler_accepts_args(registry, tmp_path):
    _write_tool(tmp_path, "echoer", (
        "name: echoer\n"
        "description: Echo args\n"
        "command: echo\n"
    ))
    load_user_tools(registry, home=tmp_path)
    entry = registry.get_entry("echoer")
    result = entry.handler({"args": "hello world"})
    assert "hello world" in result["stdout"]


def test_user_tools_dir_resolution(monkeypatch):
    import pathlib

    monkeypatch.setenv("XAVANI_HOME", "/tmp/fake-home")
    assert user_tools_dir() == pathlib.Path("/tmp/fake-home") / "tools"


# ── aggregated discovery ───────────────────────────────────────────


def test_discover_all_includes_user_tools(registry, tmp_path):
    _write_tool(tmp_path, "greet", (
        "name: greet\n"
        "description: Say hello\n"
        "command: echo hello\n"
    ))
    records = discover_all_tools(registry, home=tmp_path, include_builtin=False)
    assert any(r.source == "user-yaml" and r.name == "greet" for r in records)


def test_discovery_record_shape():
    record = DiscoveryRecord(name="x", source="user-yaml", path="/p", ok=False, error="bad")
    d = record.as_dict()
    assert d["name"] == "x"
    assert d["ok"] is False
    assert d["error"] == "bad"


def test_discover_all_builtin_idempotent(registry):
    """Repeated discovery must not duplicate registrations (builtin import
    is idempotent via importlib)."""
    records1 = discover_all_tools(registry, include_builtin=True)
    records2 = discover_all_tools(registry, include_builtin=True)
    assert records1  # builtins exist
    assert len(records1) == len(records2)
