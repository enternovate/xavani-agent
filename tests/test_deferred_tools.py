"""Tests for deferred-tool classification (Task 6).

The default tool wire omits rarely-used tools (computer_use, image/video
generation, discord/social, document, voice) and ships three meta-tools —
tool_search / tool_describe / tool_call — so deferred tools stay reachable
without paying their schema token cost on every turn. See
scripts/tool_payload_report.py for the token evidence.
"""

import json

import model_tools
from model_tools import DEFERRED_TOOL_NAMES, META_TOOL_NAMES


def _names(defs):
    return {d["function"]["name"] for d in defs}


def test_default_wire_has_meta_tools_and_no_deferred_tools():
    """(a) The default wire carries the meta-tools and omits deferred tools."""
    defs = model_tools.get_tool_definitions(enabled_toolsets=None, quiet_mode=True)
    names = _names(defs)

    # Meta-tools are ALWAYS on the wire.
    assert META_TOOL_NAMES <= names, f"missing meta-tools: {META_TOOL_NAMES - names}"

    # No deferred tool may appear on the default wire.
    assert names.isdisjoint(DEFERRED_TOOL_NAMES), (
        f"deferred tools leaked onto default wire: {names & DEFERRED_TOOL_NAMES}"
    )


def test_tool_call_dispatches_deferred_tool():
    """(b) tool_call dispatches through the registry path successfully.

    tool_describe is itself deferred-adjacent; invoking it via tool_call
    must return tool_search's full schema (harmless, no side effects).
    """
    result = model_tools.handle_function_call(
        "tool_call",
        {"name": "tool_describe", "arguments": {"name": "tool_search"}},
    )
    payload = json.loads(result)
    assert payload.get("name") == "tool_search"
    assert "parameters" in payload


def test_tool_call_unknown_tool_returns_error():
    """tool_call must return an error string for unknown tools, not raise."""
    result = model_tools.handle_function_call(
        "tool_call",
        {"name": "definitely_not_a_registered_tool", "arguments": {}},
    )
    payload = json.loads(result)
    assert "error" in payload


def test_explicit_toolset_reenables_deferred_tool():
    """(c) Explicitly enabling a deferred tool's toolset wires it back in."""
    assert "text_to_speech" in DEFERRED_TOOL_NAMES  # sanity: it IS deferred
    defs = model_tools.get_tool_definitions(enabled_toolsets=["tts"], quiet_mode=True)
    assert "text_to_speech" in _names(defs)
