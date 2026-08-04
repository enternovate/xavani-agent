# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A09: real-SQLite session store fixtures.

Shared fixtures for gateway session tests. Instead of MagicMock session
stores (which drift from the real schema), these build a real
``SessionDB`` in a per-test tempdir and wrap it in the same
``GatewaySessionStore`` the gateway uses.

Usage::

    def test_something(real_session_store):
        real_session_store.create_session("s1", source="cli")
        ...

    def test_something_else(real_session_db):
        db.append_message("s1", role="user", content="hi")
"""

from __future__ import annotations

import pytest

from xavani_state import SessionDB


@pytest.fixture
def real_session_db(tmp_path):
    """A real SessionDB on a per-test SQLite file (A09)."""
    db = SessionDB(tmp_path / "state.db")
    yield db
    try:
        db.close()
    except Exception:
        pass


@pytest.fixture
def real_session_store(tmp_path, monkeypatch):
    """A gateway session store backed by the real SQLite schema (A09).

    Redirects XAVANI_HOME so SessionStore's internal SessionDB lands on
    a per-test file, then wraps it with the same SessionStore the
    gateway uses. No MagicMock anywhere in the path.
    """
    from gateway.session import SessionStore

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path / "home"))
    store = SessionStore(
        sessions_dir=tmp_path / "sessions",
        config=None,  # type: ignore[arg-type] — store uses config lazily
    )
    assert store._db is not None, "SessionStore must open a real SessionDB"
    return store


def seed_messages(db, session_id: str, n: int = 5) -> list[int]:
    """Create a session and append n alternating user/assistant messages.

    Returns the message ids in ascending order.
    """
    db.create_session(session_id, source="cli")
    ids = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        ids.append(
            db.append_message(session_id, role=role, content=f"msg {i}")
        )
    return ids
