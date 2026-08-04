# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D10: session data lifecycle management (inactivity-based expiry).

Sessions auto-expire after N days of inactivity. Permanent sessions
(permanent=1) are exempt. last_active_at is maintained on every
message append, session reopen, and session creation.
"""

import time

import pytest

from xavani_state import SessionDB


@pytest.fixture
def db(tmp_path):
    return SessionDB(tmp_path / "state.db")


def _seed_session(db, sid, last_active=None, permanent=False):
    db.create_session(sid, source="cli")
    db.append_message(sid, role="user", content="hello")
    if last_active is not None:
        # Backdate the activity timestamp directly (append_message sets now).
        with db._lock:
            db._conn.execute(
                "UPDATE sessions SET last_active_at = ? WHERE id = ?",
                (last_active, sid),
            )
            db._conn.commit()
    if permanent:
        assert db.set_session_permanent(sid) is True
    return sid


# ── last_active_at maintenance ──────────────────────────────────────


def test_last_active_set_on_create(db):
    sid = db.create_session("s1", source="cli")
    assert db.get_last_active(sid) is not None


def test_last_active_bumped_on_append(db):
    sid = db.create_session("s1", source="cli")
    first = db.get_last_active(sid)
    time.sleep(0.01)
    db.append_message(sid, role="user", content="again")
    assert db.get_last_active(sid) > first


def test_last_active_bumped_on_reopen(db):
    sid = db.create_session("s1", source="cli")
    db.end_session(sid, end_reason="done")
    first = db.get_last_active(sid)
    time.sleep(0.01)
    db.reopen_session(sid)
    assert db.get_last_active(sid) > first


def test_get_last_active_missing_session(db):
    assert db.get_last_active("nope") is None


# ── inactivity expiry ────────────────────────────────────────────────


def test_expire_inactive_sessions_deletes_stale(db):
    stale = _seed_session(db, "stale", last_active=time.time() - (200 * 86400))
    fresh = _seed_session(db, "fresh", last_active=time.time())
    assert db.expire_inactive_sessions(inactive_days=90) == 1
    assert db.get_session(stale) is None
    assert db.get_session(fresh) is not None


def test_expire_removes_messages(db):
    stale = db.create_session("stale", source="cli")
    db.append_message(stale, role="user", content="hello")
    db.append_message(stale, role="user", content="second")
    # Backdate AFTER the appends — an append refreshes activity.
    with db._lock:
        db._conn.execute(
            "UPDATE sessions SET last_active_at = ? WHERE id = ?",
            (time.time() - (200 * 86400), stale),
        )
        db._conn.commit()
    db.expire_inactive_sessions(inactive_days=90)
    assert db.get_messages(stale) == []


def test_expire_skips_recent(db):
    _seed_session(db, "recent", last_active=time.time() - 3600)
    assert db.expire_inactive_sessions(inactive_days=90) == 0


def test_expire_skips_permanent(db):
    stale = _seed_session(
        db, "keep", last_active=time.time() - (200 * 86400), permanent=True
    )
    assert db.expire_inactive_sessions(inactive_days=90) == 0
    assert db.get_session(stale) is not None


def test_expire_covers_open_sessions(db):
    # Open (never ended) stale session must also expire.
    stale = _seed_session(db, "open", last_active=time.time() - (200 * 86400))
    assert db.expire_inactive_sessions(inactive_days=90) == 1
    assert db.get_session(stale) is None


def test_expire_orphans_child_sessions(db):
    stale = _seed_session(db, "parent", last_active=time.time() - (200 * 86400))
    child = _seed_session(db, "child", last_active=time.time())
    with db._lock:
        db._conn.execute(
            "UPDATE sessions SET parent_session_id = ? WHERE id = ?", (stale, child)
        )
        db._conn.commit()
    db.expire_inactive_sessions(inactive_days=90)
    row = db.get_session(child)
    assert row["parent_session_id"] is None


# ── permanent opt-in ────────────────────────────────────────────────


def test_set_session_permanent_roundtrip(db):
    sid = db.create_session("s1", source="cli")
    assert db.set_session_permanent(sid) is True
    with db._lock:
        row = db._conn.execute(
            "SELECT permanent FROM sessions WHERE id = ?", (sid,)
        ).fetchone()
        assert row["permanent"] == 1
    assert db.set_session_permanent(sid, permanent=False) is True
    with db._lock:
        row = db._conn.execute(
            "SELECT permanent FROM sessions WHERE id = ?", (sid,)
        ).fetchone()
        assert row["permanent"] == 0


def test_set_session_permanent_missing(db):
    assert db.set_session_permanent("ghost") is False


# ── auto-maintenance integration ─────────────────────────────────────


def test_maybe_auto_prune_expires_inactive(monkeypatch, tmp_path):
    monkeypatch.delenv("XAVANI_SESSION_EXPIRE_DAYS", raising=False)
    db = SessionDB(tmp_path / "state.db")
    stale = _seed_session(db, "stale", last_active=time.time() - (200 * 86400))
    result = db.maybe_auto_prune_and_vacuum(expire_inactive_days=90, vacuum=False)
    assert result["expired"] == 1
    assert db.get_session(stale) is None


def test_maybe_auto_prune_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_SESSION_EXPIRE_DAYS", "1")
    db = SessionDB(tmp_path / "state.db")
    stale = _seed_session(db, "stale", last_active=time.time() - (2 * 86400))
    result = db.maybe_auto_prune_and_vacuum(vacuum=False)
    assert result["expired"] == 1
    assert db.get_session(stale) is None


def test_maybe_auto_prune_expiry_disabled_with_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_SESSION_EXPIRE_DAYS", "0")
    db = SessionDB(tmp_path / "state.db")
    stale = _seed_session(db, "stale", last_active=time.time() - (200 * 86400))
    result = db.maybe_auto_prune_and_vacuum(vacuum=False)
    assert result["expired"] == 0
    assert db.get_session(stale) is not None
