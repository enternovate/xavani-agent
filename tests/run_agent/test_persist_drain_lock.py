# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A03: turn persistence drain with locking.

The whole persist-and-drain (scaffolding drop, override, JSON log, SQLite
flush) is one critical section under ``_session_persist_lock``. Close and
turn-start persistence can run on separate CLI threads; without a single
funnel both could observe the same unmarked message list and write
duplicate durable rows.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent

pytestmark = pytest.mark.integration


@pytest.fixture()
def agent(tmp_path):
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        a = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        a.client = MagicMock()
        from xavani_state import SessionDB

        a._session_db = SessionDB(tmp_path / "sessions")
        a._session_db_created = False
        a._last_flushed_db_idx = 0
        a._ensure_db_session()
        return a


def test_persist_session_uses_single_funnel_under_lock(agent):
    """The whole drain must run under _session_persist_lock (no deadlock, no split)."""
    calls = []
    real_flush = agent._flush_messages_to_session_db_unlocked

    def _wrapped_flush(messages, conversation_history=None):
        assert agent._session_persist_lock.locked(), (
            "DB flush must run while the persist lock is held"
        )
        calls.append("flush")
        return real_flush(messages, conversation_history)

    agent._flush_messages_to_session_db_unlocked = _wrapped_flush
    messages = [{"role": "user", "content": "hello"}]
    agent._persist_session(messages)
    assert calls == ["flush"]


def test_concurrent_persist_no_duplicate_rows(agent):
    """Two threads persisting the same message list must not duplicate rows."""
    messages = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
    ]
    barrier = threading.Barrier(2)

    def _persist():
        barrier.wait()
        agent._persist_session(list(messages))

    threads = [threading.Thread(target=_persist) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    rows = agent._session_db.get_messages(agent.session_id)
    contents = [r.get("content") for r in rows if r.get("role") in ("user", "assistant")]
    assert contents.count("one") == 1, f"duplicate user row: {contents}"
    assert contents.count("two") == 1, f"duplicate assistant row: {contents}"


def test_persist_session_returns_when_no_lock(agent):
    """Agents built without a persist lock keep the direct path."""
    agent._session_persist_lock = None
    messages = [{"role": "user", "content": "no-lock"}]
    agent._persist_session(messages)
    rows = agent._session_db.get_messages(agent.session_id)
    assert any(r.get("content") == "no-lock" for r in rows)
