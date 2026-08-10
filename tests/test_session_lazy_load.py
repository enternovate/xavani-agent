# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""Tail-first lazy session history load on resume (backlog A13).

On resume the CLI loads only the last N messages (XAVANI_RESUME_TAIL,
default 40) into conversation_history; older messages stay in the DB and
are fetched on demand via _fetch_older_session_messages.  Persistence is
untouched: the flush path lives in run_agent.AIAgent and keeps writing the
full working history.
"""

from unittest.mock import patch

from cli import XavaniCLI
from xavani_state import SessionDB


def _seed(db, sid="s1", n=60):
    db.create_session(sid, source="cli")
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        db.append_message(sid, role=role, content=f"msg {i}")


def _full_conversation(db, sid="s1"):
    return [m for m in db.get_messages_as_conversation(sid) if m.get("role") != "session_meta"]


def _make_cli(db, sid="s1"):
    cli = XavaniCLI()
    cli._session_db = db
    cli.session_id = sid
    cli._resumed = True
    cli.conversation_history = []
    cli._console_print = lambda *a, **k: None
    return cli


def test_resume_loads_exactly_40_messages(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=60)
    cli = _make_cli(db)
    cli._preload_resumed_session()
    assert len(cli.conversation_history) == 40


def test_resume_tail_is_the_latest_messages(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=60)
    cli = _make_cli(db)
    cli._preload_resumed_session()
    full = _full_conversation(db)
    assert cli.conversation_history == full[-40:]


def test_resume_tail_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_RESUME_TAIL", "10")
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=60)
    cli = _make_cli(db)
    cli._preload_resumed_session()
    assert len(cli.conversation_history) == 10
    assert cli.conversation_history == _full_conversation(db)[-10:]


def test_first_turn_conversation_is_the_loaded_tail(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=60)
    cli = _make_cli(db)
    with patch.object(
        db, "get_messages_as_conversation", wraps=db.get_messages_as_conversation
    ) as spy:
        cli._preload_resumed_session()
        assert spy.call_count == 1
    full = _full_conversation(db)
    assert cli.conversation_history == full[-40:]
    assert cli.conversation_history[-1] == full[-1]
    assert cli.conversation_history[0]["role"] == "user"


def test_fetch_older_returns_messages_before_the_tail(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=60)
    cli = _make_cli(db)
    cli._preload_resumed_session()
    older = cli._fetch_older_session_messages()
    full = _full_conversation(db)
    expected = full[:-40]
    assert [m["content"] for m in older] == [m["content"] for m in expected]
    assert len(older) == 20


def test_fetch_older_empty_when_tail_covers_whole_session(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=30)
    cli = _make_cli(db)
    cli._preload_resumed_session()
    assert cli._fetch_older_session_messages() == []


def test_persistence_unchanged_resume_and_fetch_never_write(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    _seed(db, n=60)
    cli = _make_cli(db)
    with patch.object(db, "append_message", wraps=db.append_message) as spy_append, patch.object(
        db, "replace_messages", wraps=db.replace_messages
    ) as spy_replace:
        cli._preload_resumed_session()
        cli._fetch_older_session_messages()
    spy_append.assert_not_called()
    spy_replace.assert_not_called()
    assert db.message_count("s1") == 60
    assert len(db.get_messages_as_conversation("s1")) == 60
