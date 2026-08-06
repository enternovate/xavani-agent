# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""G02: daily learning digest tests."""

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


def test_digest_renders_topics_and_proposals(manager):
    _seed(manager, "fix the postgres timeout", task_type="debugging", tags=["db"], outcome="done")
    _seed(manager, "write release notes", task_type="writing", tags=["docs"], outcome="done")

    digest = manager.build_daily_digest(days=1)
    assert "# Daily Learning Digest" in digest
    assert "**debugging**: 1 episode(s)" in digest
    assert "**writing**: 1 episode(s)" in digest
    assert "## Proposed skill updates" in digest
    assert "candidate for MEMORY.md" in digest


def test_digest_empty_when_no_episodes(manager):
    assert manager.build_daily_digest(days=1) == ""


def test_digest_excludes_old_episodes(manager):
    _seed(manager, "old one", task_type="debugging", outcome="done")
    rows = manager.episodic._get_conn().execute(
        "SELECT episode_id FROM episodes ORDER BY id LIMIT 1"
    ).fetchone()
    manager.episodic._get_conn().execute(
        "UPDATE episodes SET timestamp = '2020-01-01T00:00:00+00:00' WHERE episode_id = ?",
        (rows[0],),
    )
    assert manager.build_daily_digest(days=1) == ""
