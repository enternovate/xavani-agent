# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the deterministic per-turn tool pre-filter (v0.4.0 U8)."""

from __future__ import annotations

import inspect

from tools.tool_prefilter import filter_definitions, select_tools

ALL_TOOLS = [
    "read_file", "write_file", "edit_file", "terminal_tool", "todo_tool",
    "clarify_tool", "browser_cdp_tool", "web_tools", "x_search_tool",
    "image_generation_tool", "vision_tools", "video_generation_tool",
    "tts_tool", "transcription_tools", "voice_mode", "memory_tool",
    "session_search_tool", "send_message_tool", "discord_tool",
    "cronjob_tools", "mcp_tool", "eval_harness_tool",
    "mixture_of_agents_tool", "delegate_tool", "skill_manager_tool",
    "computer_use_tool", "homeassistant_tool",
]


def test_empty_text_returns_full_set():
    assert select_tools("", ALL_TOOLS) == ALL_TOOLS
    assert select_tools("   ", ALL_TOOLS) == ALL_TOOLS


def test_no_intent_returns_full_set():
    # No recognizable tool intent -> never hide tools.
    assert select_tools("hello, how are you today?", ALL_TOOLS) == ALL_TOOLS


def test_browse_intent_selects_browser_and_essentials_and_reduces():
    result = select_tools("browse example.com and take a screenshot", ALL_TOOLS)
    assert "browser_cdp_tool" in result          # intent: browse
    assert "image_generation_tool" in result     # intent: screenshot/image
    assert "vision_tools" in result
    assert "read_file" in result                 # essential always included
    assert "memory_tool" in result               # essential always included
    assert "homeassistant_tool" not in result    # unrelated -> filtered
    assert "cronjob_tools" not in result
    assert len(result) < len(ALL_TOOLS)          # it actually reduced the set


def test_order_preserved_and_deterministic():
    a = select_tools("run a python script and search the web", ALL_TOOLS)
    b = select_tools("run a python script and search the web", ALL_TOOLS)
    assert a == b                                # deterministic
    # result is a subsequence of the input order
    idx = [ALL_TOOLS.index(t) for t in a]
    assert idx == sorted(idx)


def test_filter_definitions_handles_both_schema_shapes():
    defs = [
        {"name": "browser_cdp_tool"},
        {"function": {"name": "homeassistant_tool"}},
        {"name": "read_file"},
    ]
    kept = filter_definitions("browse a website", defs)
    names = {
        d.get("name") or d.get("function", {}).get("name")
        for d in kept
    }
    assert "browser_cdp_tool" in names
    assert "read_file" in names                  # essential
    assert "homeassistant_tool" not in names     # unrelated -> filtered


def test_prefilter_makes_no_llm_calls():
    import ast

    import tools.tool_prefilter as m

    tree = ast.parse(inspect.getsource(m))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden_roots = {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq"}
    assert not (imported & forbidden_roots), (
        f"tool_prefilter imports an LLM client: {imported & forbidden_roots}"
    )
    src = inspect.getsource(m)
    for pattern in (".chat.completions", ".messages.create", "acompletion("):
        assert pattern not in src, f"tool_prefilter must stay LLM-free (found {pattern})"
