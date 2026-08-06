# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B05: episodic summarization + MEMORY.md promotion proposals."""

from __future__ import annotations

import pytest

from xavani_memory.manager import MemoryManager


@pytest.fixture
def manager(tmp_path):
    m = MemoryManager(memory_dir=tmp_path / "memory", auto_maintenance=False)
    m.set_session("test-session")
    yield m
    try:
        m.stop_maintenance()
    except Exception:
        pass


def _seed(manager, text, *, task_type=None, tags=None, outcome=None):
    manager.remember(
        user_input=text,
        agent_response="ok",
        outcome=outcome,
        tags=tags,
        metadata={"task_type": task_type} if task_type else None,
    )


def test_summarize_groups_by_topic(manager):
    _seed(manager, "fix the postgres timeout", task_type="debugging", tags=["db"], outcome="done")
    _seed(manager, "another timeout", task_type="debugging", tags=["db"], outcome="done")
    _seed(manager, "write release notes", task_type="writing", tags=["docs"], outcome="done")

    summary = manager.summarize_recent_episodes(days=7)
    topics = {row["topic"]: row for row in summary}
    assert topics["debugging"]["count"] == 2
    assert topics["debugging"]["completed"] == 2
    assert topics["writing"]["count"] == 1
    assert "db" in topics["debugging"]["top_tags"]


def test_summarize_excludes_old_episodes(manager):
    _seed(manager, "recent one", task_type="debugging", outcome="done")
    # Backdate an episode beyond the 7-day window.
    rows = manager.episodic._get_conn().execute(
        "SELECT episode_id FROM episodes ORDER BY id LIMIT 1"
    ).fetchone()
    manager.episodic._get_conn().execute(
        "UPDATE episodes SET timestamp = '2020-01-01T00:00:00+00:00' WHERE episode_id = ?",
        (rows[0],),
    )
    summary = manager.summarize_recent_episodes(days=7)
    assert not summary


def test_propose_memory_entries_renders_bullets(manager):
    _seed(manager, "fix the postgres timeout", task_type="debugging", tags=["db"], outcome="done")
    summary = manager.summarize_recent_episodes(days=7)
    entries = manager.propose_memory_entries(summary)
    assert entries
    assert "debugging" in entries[0]
    assert "candidate for MEMORY.md" in entries[0]
    assert "1 recent episode(s) (1 completed)" in entries[0]


def test_propose_respects_max_entries(manager):
    for i in range(4):
        _seed(manager, f"task {i}", task_type=f"type{i}", outcome="done")
    summary = manager.summarize_recent_episodes(days=7)
    assert len(manager.propose_memory_entries(summary, max_entries=2)) == 2


def test_general_topic_when_no_metadata(manager):
    manager.remember(user_input="hello", agent_response="hi")
    summary = manager.summarize_recent_episodes(days=7)
    assert summary[0]["topic"] == "general"
