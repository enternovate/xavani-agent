# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A03: ContextVar verification harness — applied to every module.

Each module that uses ContextVars for session state must pass the
harness: thread isolation, default fallback, copy_context propagation,
asyncio isolation, and token reset. A regression here means concurrent
gateway sessions can bleed state into each other.
"""

import pytest

from tests.xavani_state.contextvar_harness import check_contextvar_semantics


def _assert_clean(var, set_value, default=None, label=""):
    problems = check_contextvar_semantics(var, set_value, default=default)
    assert problems == [], f"{label or var}: {problems}"


# ── gateway/session_context.py — the 12 session vars ─────────────────


def test_gateway_session_context_vars():
    import gateway.session_context as sc

    assert len(sc._VAR_MAP) >= 10, "session var map shrank unexpectedly"
    for name, var in sc._VAR_MAP.items():
        problems = check_contextvar_semantics(var, "sess-1", default="UNSET")
        assert problems == [], f"{name}: {problems}"


def test_session_env_fallback_to_os_environ(monkeypatch):
    """Never-set vars fall back to os.environ (CLI/cron compat)."""
    import gateway.session_context as sc

    monkeypatch.setenv("XAVANI_SESSION_PLATFORM", "telegram")
    assert sc.get_session_env("XAVANI_SESSION_PLATFORM") == "telegram"
    # Explicitly set vars do NOT fall back, even to empty string.
    tokens = sc.set_session_vars(platform="discord")
    try:
        assert sc.get_session_env("XAVANI_SESSION_PLATFORM") == "discord"
    finally:
        sc.clear_session_vars(tokens)


# ── tools/approval.py ────────────────────────────────────────────────


def test_approval_session_key():
    from tools.approval import (
        _approval_session_key,
        get_current_session_key,
        reset_current_session_key,
        set_current_session_key,
    )

    _assert_clean(_approval_session_key, "session-42", default="")

    token = set_current_session_key("session-42")
    try:
        assert get_current_session_key() == "session-42"
    finally:
        reset_current_session_key(token)
    assert get_current_session_key(default="default") == "default"


# ── xavani_constants.py ─────────────────────────────────────────────


def test_xavani_home_override_var():
    import xavani_constants as xc

    _assert_clean(xc._XAVANI_HOME_OVERRIDE, "/tmp/home-x", default="UNSET")

    token = xc.set_xavani_home_override("/tmp/home-x")
    try:
        assert xc.get_xavani_home_override() == "/tmp/home-x"
    finally:
        xc.reset_xavani_home_override(token)
    assert xc.get_xavani_home_override() is None


# ── tools/env_passthrough.py ────────────────────────────────────────


def test_allowed_env_vars_var():
    from tools.env_passthrough import _allowed_env_vars_var

    _assert_clean(_allowed_env_vars_var, {"OPENAI_API_KEY"}, default="UNSET")


# ── tools/credential_files.py ───────────────────────────────────────


def test_registered_files_var():
    from tools.credential_files import _registered_files_var

    _assert_clean(_registered_files_var, {"/tmp/creds.json": "creds.json"}, default="UNSET")


# ── tools/skill_provenance.py ───────────────────────────────────────


def test_write_origin_var():
    from tools.skill_provenance import _write_origin

    _assert_clean(_write_origin, "background_review", default="foreground")


# ── gateway/platforms/slack.py ──────────────────────────────────────


def test_slash_user_id_var():
    from gateway.platforms.slack import _slash_user_id

    _assert_clean(_slash_user_id, "U123", default=None)


# ── tool_executor propagation contract ──────────────────────────────


def test_tool_executor_copies_context_for_executor_threads():
    """tool_executor.py:299-300 copies the context into executor threads.

    A value set in the agent context must reach a copy_context() child —
    this is the exact mechanism approval + session vars rely on when a
    tool runs in a ThreadPoolExecutor.
    """
    import contextvars
    import threading

    from tools.approval import _approval_session_key

    token = _approval_session_key.set("exec-session")
    try:
        seen: list = []

        def _worker():
            seen.append(_approval_session_key.get())

        ctx = contextvars.copy_context()
        t = threading.Thread(target=lambda: ctx.run(_worker))
        t.start()
        t.join()
        assert seen == ["exec-session"]
    finally:
        _approval_session_key.reset(token)


# ── harness self-test (the tester must catch violations) ────────────


class _FakeContextVar:
    """Duck-typed ContextVar with an injectable bug for harness self-tests."""

    def __init__(self, name, default=None, bug=None):
        self.name = name
        self._default = default
        self._bug = bug or {}
        self._values: dict = {}

    def set(self, value):
        token = ("tok", id(self._values), len(self._values))
        self._values[token] = value
        if self._bug.get("leak"):
            self._bug["leaked_value"] = value
        if self._bug.get("no_reset"):
            self._bug["no_reset_token"] = token
        return token

    def get(self):
        if self._bug.get("leak") and "leaked_value" in self._bug:
            return self._bug["leaked_value"]
        if self._values:
            return next(reversed(self._values.values()))
        if self._default is not None:
            return self._default
        raise LookupError(self.name)

    def reset(self, token):
        if self._bug.get("no_reset"):
            return None  # the bug: reset no-ops
        self._values.pop(token, None)


def test_harness_detects_thread_leak():
    """A broken (leaky) ContextVar must be flagged by the harness."""
    leaky = _FakeContextVar("leaky", bug={"leak": True})
    problems = check_contextvar_semantics(leaky, "v1", default="UNSET")
    assert problems, "harness must flag the simulated leak"
    assert any("leaked" in p for p in problems)


def test_harness_detects_reset_violation():
    """A token-reset regression must be flagged by the harness."""
    var = _FakeContextVar("no_reset", bug={"no_reset": True})
    problems = check_contextvar_semantics(var, "v2", default="UNSET")
    assert problems, "harness must flag the reset regression"
    assert any("reset" in p for p in problems)
