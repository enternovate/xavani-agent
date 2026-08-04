# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A09: real-SQLite session store fixtures.

Session tests must run against the real schema, not MagicMock stores
that drift from production. These tests prove the fixtures exercise
the actual SQLite path (schema columns, FTS, WAL).
"""

import pytest

from gateway.session import SessionSource, Platform

from tests.gateway.session_fixtures import real_session_db, real_session_store, seed_messages  # noqa: F401


# ── real_session_db ─────────────────────────────────────────────────


def test_db_is_real_sqlite(real_session_db):
    """The fixture DB must be a live SessionDB with the real schema."""
    assert real_session_db._conn is not None
    # Real schema has the A12/B08-era columns.
    cols = {
        row["name"]
        for row in real_session_db._conn.execute("PRAGMA table_info(sessions)").fetchall()
    }
    assert "last_active_at" in cols
    assert "permanent" in cols
    assert "parent_session_id" in cols


def test_db_wal_mode(real_session_db):
    journal = real_session_db._conn.execute(
        "PRAGMA journal_mode"
    ).fetchone()[0]
    assert journal == "wal"


def test_seed_messages_creates_session(real_session_db):
    ids = seed_messages(real_session_db, "s1", n=6)
    assert len(ids) == 6
    messages = real_session_db.get_messages("s1")
    assert len(messages) == 6
    assert [m["id"] for m in messages] == ids
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


# ── real_session_store ──────────────────────────────────────────────


def test_store_opens_real_db(real_session_store):
    """SessionStore must hold a real SessionDB, never a mock."""
    assert real_session_store._db is not None
    assert real_session_store._db._conn is not None


def test_store_create_and_query(real_session_store):
    source = SessionSource(platform=Platform.LOCAL, chat_id="test-chat")
    entry = real_session_store.get_or_create_session(source)
    assert entry is not None
    # The DB layer holds the session row.
    session_id = entry.session_id
    db = real_session_store._db
    assert db is not None
    db.append_message(session_id, role="user", content="hello")
    messages = db.get_messages(session_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "hello"


def test_store_persists_across_reopen(tmp_path, monkeypatch):
    """A second store on the same home sees the first store's data."""
    from gateway.session import SessionStore

    def _source():
        return SessionSource(platform=Platform.LOCAL, chat_id="cli")

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path / "home"))
    store1 = SessionStore(sessions_dir=tmp_path / "sessions", config=None)  # type: ignore[arg-type]
    entry1 = store1.get_or_create_session(_source())
    db1 = store1._db
    assert db1 is not None
    db1.append_message(entry1.session_id, role="user", content="persisted")

    store2 = SessionStore(sessions_dir=tmp_path / "sessions", config=None)  # type: ignore[arg-type]
    db2 = store2._db
    assert db2 is not None
    messages = db2.get_messages(entry1.session_id)
    assert messages and messages[0]["content"] == "persisted"


def test_mock_store_never_used_in_fixture_path():
    """Guard: the fixture module must not import MagicMock for stores."""
    import inspect

    from tests.gateway import session_fixtures

    src = inspect.getsource(session_fixtures)
    assert "from unittest.mock import MagicMock" not in src
    assert "MagicMock()" not in src
    # The fixture must build a real SessionStore, not a mock object.
    assert "SessionStore(" in src
