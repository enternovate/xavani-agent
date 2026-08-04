# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for expandable stack traces (E07).

``XAVANI_FULL_TRACEBACK=1`` switches cli.py's exception formatting from
concise ``Error: <message>`` one-liners to full tracebacks, so debugging
sessions can expand the stack without restarting with a different verbosity.
"""

import os

import pytest

from cli import _format_cli_exception, _full_traceback_enabled


def _call_inside_traceback():
    raise ValueError("boom from deep")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("garbage", False),
    ],
)
def test_full_traceback_enabled_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("XAVANI_FULL_TRACEBACK", value)
    assert _full_traceback_enabled() is expected


def test_full_traceback_enabled_when_unset(monkeypatch):
    monkeypatch.delenv("XAVANI_FULL_TRACEBACK", raising=False)
    assert _full_traceback_enabled() is False


def test_concise_format_by_default(monkeypatch):
    monkeypatch.delenv("XAVANI_FULL_TRACEBACK", raising=False)
    with pytest.raises(ValueError) as excinfo:
        _call_inside_traceback()
    formatted = _format_cli_exception(excinfo.value)
    assert formatted == "Error: boom from deep"
    assert "Traceback" not in formatted


def test_full_traceback_when_env_enabled(monkeypatch):
    monkeypatch.setenv("XAVANI_FULL_TRACEBACK", "1")
    with pytest.raises(ValueError) as excinfo:
        _call_inside_traceback()
    formatted = _format_cli_exception(excinfo.value)
    assert formatted.startswith("Error:")
    assert "Traceback (most recent call last)" in formatted
    assert "boom from deep" in formatted
    # The traceback must show the helper frame, proving it's a real stack.
    assert "_call_inside_traceback" in formatted
