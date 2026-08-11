# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E08: tool-level health checks — registry health_fn aggregation."""

from tools.registry import ToolRegistry, ToolEntry
import pytest

pytestmark = pytest.mark.unit


def _make_registry():
    r = ToolRegistry()
    r._lock.acquire()
    try:
        r._tools.clear()
    finally:
        r._lock.release()
    return r


def _register(registry, name, health_fn=None):
    registry.register(
        name=name,
        toolset="test",
        schema={"name": name, "description": "t"},
        handler=lambda **kw: "ok",
        health_fn=health_fn,
    )


def test_no_health_fn_returns_none():
    r = _make_registry()
    _register(r, "plain")
    assert r.get_tool_health("plain") is None


def test_dict_health_fn():
    r = _make_registry()
    _register(r, "healthy", lambda: {"ok": True, "detail": "all good"})
    result = r.get_tool_health("healthy")
    assert result == {"ok": True, "detail": "all good"}


def test_bool_health_fn_normalized():
    r = _make_registry()
    _register(r, "ok_tool", lambda: True)
    _register(r, "bad_tool", lambda: False)
    assert r.get_tool_health("ok_tool") == {"ok": True, "detail": ""}
    assert r.get_tool_health("bad_tool") == {"ok": False, "detail": ""}


def test_health_fn_exception_reported_not_raised():
    r = _make_registry()

    def boom():
        raise RuntimeError("probe crashed")

    _register(r, "crashed", boom)
    result = r.get_tool_health("crashed")
    assert result is not None
    assert result["ok"] is False
    assert "RuntimeError" in result["detail"]


def test_health_fn_defaults_ok_false():
    r = _make_registry()
    _register(r, "partial", lambda: {"detail": "no ok key"})
    result = r.get_tool_health("partial")
    assert result is not None
    assert result["ok"] is False


def test_missing_tool_returns_none():
    r = _make_registry()
    assert r.get_tool_health("ghost") is None


def test_get_all_tool_health_only_health_tools():
    r = _make_registry()
    _register(r, "with_health", lambda: {"ok": True})
    _register(r, "without_health")
    result = r.get_all_tool_health()
    assert "with_health" in result
    assert "without_health" not in result


def test_terminal_tool_registered_health_fn():
    """The real terminal tool must expose a health probe (E08)."""
    import tools.terminal_tool  # noqa: F401 — triggers registration

    from tools.registry import registry

    entry = registry.get_entry("terminal")
    assert entry is not None
    assert entry.health_fn is not None
    result = entry.health_fn()
    assert "ok" in result
    assert "detail" in result
