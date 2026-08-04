# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D13: sanitizer for LLM-generated execution input.

Code arguments wrapped in markdown fences must be unwrapped before
execution — and any trailing prose after the closing fence must be
dropped, never executed.
"""

import json

import pytest

from tools.command_sanitizer import (
    has_fenced_block,
    sanitize_execution_input,
    sanitize_shell_command,
)


# ── has_fenced_block ────────────────────────────────────────────────


def test_no_fence_false():
    assert has_fenced_block("print('hello')") is False


def test_empty_false():
    assert has_fenced_block("") is False


def test_python_fence_true():
    assert has_fenced_block("```python\nprint(1)\n```") is True


def test_tilde_fence_true():
    assert has_fenced_block("~~~bash\necho hi\n~~~") is True


# ── sanitize_execution_input ────────────────────────────────────────


def test_plain_code_passes_through():
    code = "print('hello')"
    assert sanitize_execution_input(code) == code


def test_fenced_python_extracts_body():
    code = "```python\nprint(1)\nprint(2)\n```"
    assert sanitize_execution_input(code) == "print(1)\nprint(2)"


def test_fence_with_language_tag_strips_tag():
    code = "```python\nx = 1\n```"
    assert sanitize_execution_input(code) == "x = 1"


def test_trailing_prose_after_fence_is_dropped():
    # The injection vector: prose after the closing fence must NOT run.
    code = "```python\nprint('safe')\n```\nrm -rf / && echo pwned"
    assert sanitize_execution_input(code) == "print('safe')"


def test_leading_prose_before_fence_ignored():
    code = "Here is the script:\n```python\nprint('ok')\n```"
    assert sanitize_execution_input(code) == "print('ok')"


def test_empty_fence_body_falls_back_to_raw():
    code = "```python\n```"
    assert sanitize_execution_input(code) == code


def test_none_input_returns_empty():
    assert sanitize_execution_input(None) == ""  # type: ignore[arg-type]


def test_tilde_fence_extracts():
    code = "~~~python\nx = 2\n~~~"
    assert sanitize_execution_input(code) == "x = 2"


def test_unclosed_fence_returns_body():
    code = "```python\nprint('no close')\n"
    assert sanitize_execution_input(code) == "print('no close')"


def test_multiple_fences_first_wins():
    code = "```python\nfirst()\n```\n```python\nsecond()\n```"
    assert sanitize_execution_input(code) == "first()"


# ── sanitize_shell_command ──────────────────────────────────────────


def test_shell_command_unwrapped():
    cmd = "```bash\nls -la\n```"
    assert sanitize_shell_command(cmd) == "ls -la"


def test_shell_plain_passthrough():
    assert sanitize_shell_command("ls -la") == "ls -la"


# ── execute_code integration ────────────────────────────────────────


def test_execute_code_unwraps_fence_before_dispatch(monkeypatch):
    """execute_code must sanitize before dispatch — a fenced argument
    reaches the backend as clean code."""
    import tools.code_execution_tool as cet

    captured = {}

    def fake_sanitize(code):
        captured["seen"] = code
        return "print('clean')"

    monkeypatch.setattr(cet, "SANDBOX_AVAILABLE", True)
    # Lazy import inside execute_code — patch the source module, not the
    # importing module (tools.command_sanitizer.sanitize_execution_input).
    monkeypatch.setattr(
        "tools.command_sanitizer.sanitize_execution_input",
        fake_sanitize,
        raising=True,
    )

    # Force the remote path so we can intercept at the dispatch boundary
    # without a real sandbox. Lazy import from terminal_tool.
    def fake_env_config():
        return {"env_type": "remote"}

    monkeypatch.setattr("tools.terminal_tool._get_env_config", fake_env_config, raising=True)

    def fake_execute_remote(code, task_id, enabled_tools):
        captured["dispatched"] = code
        return json.dumps({"ok": True})

    monkeypatch.setattr(cet, "_execute_remote", fake_execute_remote)

    result = cet.execute_code("```python\nprint(1)\n```\nrm -rf /")
    assert captured["seen"] == "```python\nprint(1)\n```\nrm -rf /"
    # The sanitized code is what gets dispatched.
    assert captured["dispatched"] == "print('clean')"
    assert json.loads(result)["ok"] is True


def test_execute_code_empty_after_sanitize_errors(monkeypatch):
    import tools.code_execution_tool as cet

    monkeypatch.setattr(cet, "SANDBOX_AVAILABLE", True)
    monkeypatch.setattr(
        "tools.command_sanitizer.sanitize_execution_input",
        lambda code: "",
        raising=True,
    )
    result = cet.execute_code("```\n```")
    payload = json.loads(result)
    assert "error" in payload
