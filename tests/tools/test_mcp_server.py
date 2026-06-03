# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for MCP server hosting of the tool registry (v0.4.0 U32)."""

from __future__ import annotations

import pytest

from tools import mcp_server


def test_exposed_specs_are_well_formed_and_deterministic():
    specs = mcp_server.exposed_tool_specs()
    assert specs, "expected at least one exposed tool"
    names = [s["name"] for s in specs]
    assert names == sorted(names)                 # deterministic ordering
    assert len(names) == len(set(names))          # no duplicates
    for s in specs:
        assert isinstance(s["name"], str) and s["name"]
        assert isinstance(s["description"], str)
        assert isinstance(s["inputSchema"], dict)


def test_meta_and_agentloop_tools_are_not_exposed():
    names = {s["name"] for s in mcp_server.exposed_tool_specs()}
    assert "guidelines_gate" not in names
    assert "delegate" not in names


def test_tool_objects_build_from_specs():
    pytest.importorskip("mcp")
    specs = mcp_server.exposed_tool_specs()
    objs = mcp_server._mcp_tool_objects(specs)
    assert len(objs) == len(specs)
    assert {o.name for o in objs} == {s["name"] for s in specs}
    # inputSchema is carried through verbatim
    by_name = {o.name: o for o in objs}
    sample = specs[0]
    assert by_name[sample["name"]].inputSchema == sample["inputSchema"]


def test_text_result_wraps_content():
    pytest.importorskip("mcp")
    out = mcp_server._text_result("hello world")
    assert len(out) == 1
    assert out[0].type == "text"
    assert out[0].text == "hello world"


def test_build_server_constructs():
    pytest.importorskip("mcp")
    server = mcp_server.build_server("xavani-test")
    assert server is not None
    assert hasattr(server, "create_initialization_options")
