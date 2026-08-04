# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E09: LLM-as-debugger tests."""

import json

from xavani_observability.debug_brief import (
    MAX_LOG_TAIL,
    _log_tail,
    _trim_context,
    brief_to_json,
    build_debug_brief,
    render_brief,
)


# ── log tail ───────────────────────────────────────────────────────


def test_log_tail_last_lines():
    logs = [f"line {i}" for i in range(100)]
    tail = _log_tail(logs, limit=10)
    assert len(tail) == 10
    assert tail[0] == "line 90"
    assert tail[-1] == "line 99"


def test_log_tail_empty():
    assert _log_tail([]) == []


def test_log_tail_default_limit():
    logs = [f"line {i}" for i in range(100)]
    assert len(_log_tail(logs)) == MAX_LOG_TAIL


# ── context trimming ───────────────────────────────────────────────


def test_context_trimmed_to_keys():
    context = {f"key{i}": i for i in range(100)}
    trimmed = _trim_context(context)
    assert len(trimmed) == 30


def test_context_values_stringified():
    assert _trim_context({"n": 42, "b": True}) == {"n": "42", "b": "True"}


def test_context_empty():
    assert _trim_context(None) == {}
    assert _trim_context({}) == {}


# ── brief building ─────────────────────────────────────────────────


def test_build_brief_shape():
    brief = build_debug_brief(
        "TimeoutError: read timed out",
        context={"tool": "terminal", "command": "curl x"},
        log_tail=["2026-08-04 error 1", "2026-08-04 error 2"],
        task_id="t-42",
    )
    assert brief["error"] == "TimeoutError: read timed out"
    assert brief["task_id"] == "t-42"
    assert brief["context"]["tool"] == "terminal"
    assert brief["log_tail"] == ["2026-08-04 error 1", "2026-08-04 error 2"]
    assert "python" in brief["environment"]
    assert brief["generated_at"] > 0


def test_build_brief_minimal():
    brief = build_debug_brief("boom")
    assert brief["error"] == "boom"
    assert brief["log_tail"] == []
    assert brief["traceback"] == ""


def test_build_brief_includes_traceback():
    brief = build_debug_brief("boom", traceback_text="Traceback (most recent call last):\n...")
    assert "Traceback" in brief["traceback"]


# ── rendering ──────────────────────────────────────────────────────


def test_render_brief_contains_sections():
    brief = build_debug_brief(
        "boom",
        context={"tool": "x"},
        log_tail=["err line"],
    )
    text = render_brief(brief)
    assert "=== Debug Brief ===" in text
    assert "Error: boom" in text
    assert "tool: x" in text
    assert "err line" in text
    assert "Environment:" in text


def test_render_brief_task_id():
    brief = build_debug_brief("boom", task_id="t-7")
    assert "Task: t-7" in render_brief(brief)


def test_render_brief_log_cap():
    brief = build_debug_brief("boom", log_tail=[f"l{i}" for i in range(60)])
    text = render_brief(brief, max_log_lines=5)
    assert text.count("l5") == 0  # only the last 5 lines rendered


# ── serialization ──────────────────────────────────────────────────


def test_brief_to_json_round_trip():
    brief = build_debug_brief("boom", context={"a": 1})
    parsed = json.loads(brief_to_json(brief))
    assert parsed["error"] == "boom"
    assert parsed["context"]["a"] == "1"
