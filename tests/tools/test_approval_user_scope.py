# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D07: per-user approval escalation thread model.

Approval state in shared multi-user sessions must not leak between
users: user A's approval never grants user B the same pattern.
"""

import pytest

from tools.approval import (
    _session_approved,
    _session_approved_by_user,
    approve_session_for_user,
    clear_session,
    is_approved_for_user,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_state():
    with __import__("tools.approval", fromlist=["_lock"])._lock:
        _session_approved.clear()
        _session_approved_by_user.clear()
    yield
    with __import__("tools.approval", fromlist=["_lock"])._lock:
        _session_approved.clear()
        _session_approved_by_user.clear()


def test_user_approval_isolated_from_other_user():
    approve_session_for_user("shared-session", "user-A", "pattern:curl")
    assert is_approved_for_user("shared-session", "user-A", "pattern:curl") is True
    assert is_approved_for_user("shared-session", "user-B", "pattern:curl") is False


def test_user_approval_isolated_across_sessions():
    approve_session_for_user("session-1", "user-A", "pattern:x")
    assert is_approved_for_user("session-2", "user-A", "pattern:x") is False


def test_session_wide_approval_covers_all_users():
    from tools.approval import approve_session

    approve_session("shared", "pattern:y")
    assert is_approved_for_user("shared", "user-A", "pattern:y") is True
    assert is_approved_for_user("shared", "user-B", "pattern:y") is True


def test_no_user_id_falls_back_to_session_scope():
    from tools.approval import approve_session

    approve_session("solo", "pattern:z")
    assert is_approved_for_user("solo", "", "pattern:z") is True


def test_unknown_pattern_not_approved():
    assert is_approved_for_user("s", "u", "pattern:nope") is False


def test_clear_session_wipes_user_state():
    approve_session_for_user("shared", "user-A", "pattern:curl")
    clear_session("shared")
    assert is_approved_for_user("shared", "user-A", "pattern:curl") is False


def test_user_state_storage_shape():
    approve_session_for_user("shared", "user-A", "p1")
    approve_session_for_user("shared", "user-B", "p1")
    assert _session_approved_by_user["shared"]["user-A"] == {"p1"}
    assert _session_approved_by_user["shared"]["user-B"] == {"p1"}


def test_user_scope_key():
    from tools.approval import _user_scope_key

    assert _user_scope_key("s", "u") == "s::u"
    assert _user_scope_key("s", "") == "s"
