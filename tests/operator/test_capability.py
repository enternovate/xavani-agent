# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the capability layer — agent tools + skills wired into the operator
(v0.7.0 operator M-Biz foundation)."""

from __future__ import annotations

from xavani_operator.capability import Capabilities


class _FakeRegistry:
    def __init__(self, names):
        self._names = names
        self.calls = []

    def get_all_tool_names(self):
        return self._names

    def dispatch(self, name, args):
        self.calls.append((name, args))
        return f"ran {name}"


def test_lists_available_tools():
    cap = Capabilities(registry=_FakeRegistry(["image_generation_tool", "web_tools", "send_message_tool"]))
    assert "web_tools" in cap.tools()
    assert cap.has_tool("web_tools")
    assert not cap.has_tool("nope")


def test_invoke_tool_dispatches_to_registry():
    reg = _FakeRegistry(["x_tool"])
    cap = Capabilities(registry=reg)
    out = cap.invoke_tool("x_tool", {"a": 1})
    assert "ran x_tool" in out
    assert reg.calls == [("x_tool", {"a": 1})]


def test_lists_injected_skills():
    cap = Capabilities(registry=_FakeRegistry([]), skill_names=["canvas-design", "frontend-design"])
    assert "canvas-design" in cap.skills()


def test_find_surfaces_relevant_tools_and_skills():
    cap = Capabilities(
        registry=_FakeRegistry(["image_generation_tool", "web_tools", "terminal_tool"]),
        skill_names=["canvas-design", "python-testing"],
    )
    rel = cap.find("create an image poster design")
    assert "image_generation_tool" in rel["tools"]
    assert "canvas-design" in rel["skills"]
    assert "python-testing" not in rel["skills"]


def test_as_context_lists_capabilities():
    cap = Capabilities(registry=_FakeRegistry(["web_tools"]), skill_names=["canvas-design"])
    ctx = cap.as_context()
    assert "web_tools" in ctx
    assert "canvas-design" in ctx


def test_missing_registry_degrades_gracefully():
    # No registry + a registry that raises -> empty tools, never crashes.
    class _Broken:
        def get_all_tool_names(self):
            raise RuntimeError("registry unavailable")

    cap = Capabilities(registry=_Broken())
    assert cap.tools() == []
