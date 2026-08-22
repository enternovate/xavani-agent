# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools/approval.py batch preview and batch approval."""

import pytest

from tools import approval


@pytest.fixture(autouse=True)
def _isolate_session(monkeypatch):
    monkeypatch.setattr(approval, "get_current_session_key", lambda: "test-session")
    approval.clear_session("test-session")


def test_preview_batch_passes_safe_commands():
    result = approval.preview_batch(["ls -la", "echo hi"])
    assert result["pending"] == []
    assert result["blocked"] == []


def test_preview_batch_flags_dangerous_and_hardline():
    dangerous = "git push --force origin main"
    hardline = "rm -rf /"
    result = approval.preview_batch([dangerous, hardline])
    assert len(result["pending"]) == 1
    assert result["pending"][0]["command"] == dangerous
    assert result["pending"][0]["pattern_key"]
    assert len(result["blocked"]) == 1
    assert result["blocked"][0]["command"] == hardline


def test_preview_batch_skips_session_approved_patterns():
    cmd = "git push --force origin main"
    first = approval.preview_batch([cmd])
    assert len(first["pending"]) == 1
    approval.approve_session("test-session", first["pending"][0]["pattern_key"])
    second = approval.preview_batch([cmd])
    assert second["pending"] == []


def test_approve_batch_empty_pending_is_true():
    assert approval.approve_batch([]) is True


def test_approve_batch_once_keeps_state_clean(monkeypatch):
    pending = [{"command": "cmd-a", "pattern_key": "pat-a", "description": "d"}]
    monkeypatch.setattr(
        approval, "prompt_dangerous_approval", lambda *a, **k: "once"
    )
    assert approval.approve_batch(pending) is True
    assert not approval.is_approved("test-session", "pat-a")


def test_approve_batch_session_covers_all(monkeypatch):
    pending = [
        {"command": "cmd-a", "pattern_key": "pat-a", "description": "d"},
        {"command": "cmd-b", "pattern_key": "pat-b", "description": "d"},
    ]
    monkeypatch.setattr(
        approval, "prompt_dangerous_approval", lambda *a, **k: "session"
    )
    assert approval.approve_batch(pending) is True
    assert approval.is_approved("test-session", "pat-a")
    assert approval.is_approved("test-session", "pat-b")


def test_approve_batch_deny_returns_false(monkeypatch):
    pending = [{"command": "cmd-a", "pattern_key": "pat-x", "description": "d"}]
    monkeypatch.setattr(
        approval, "prompt_dangerous_approval", lambda *a, **k: "deny"
    )
    assert approval.approve_batch(pending) is False
    assert not approval.is_approved("test-session", "pat-x")
