# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""G04: follow-up question queue tests."""

from __future__ import annotations

import pytest

from agent.followup_queue import FollowUpQueue


@pytest.fixture
def queue(tmp_path):
    return FollowUpQueue(path=str(tmp_path / "followups.jsonl"))


def test_record_appends_and_pending_returns_oldest_first(queue):
    assert queue.record("Should I continue with the refactor?")
    assert queue.record("Want me to draft the release notes?", session_id="s1")
    pending = queue.pending()
    assert len(pending) == 2
    assert pending[0]["question"] == "Should I continue with the refactor?"
    assert pending[0]["session_id"] == ""
    assert pending[1]["session_id"] == "s1"
    assert pending[0]["answered"] is False


def test_pending_limit(queue):
    for i in range(5):
        queue.record(f"Question {i}?")
    assert len(queue.pending(limit=2)) == 2


def test_record_rejects_empty(queue):
    assert queue.record("   ") is False
    assert queue.pending() == []


def test_mark_answered_removes_from_pending(queue):
    queue.record("Still there?")
    qid = queue.pending()[0]["id"]
    assert queue.mark_answered(qid) is True
    assert queue.pending() == []


def test_pending_survives_corrupt_line(queue):
    queue.record("Good question?")
    with open(queue._path, "a", encoding="utf-8") as f:
        f.write("{not json}\n")
    assert len(queue.pending()) == 1
