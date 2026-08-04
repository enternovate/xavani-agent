# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G06: agent-initiated continuation tests."""

import pytest

from tools.continuation_store import ContinuationStore


@pytest.fixture
def store(tmp_path):
    return ContinuationStore(home=tmp_path)


# ── requesting ─────────────────────────────────────────────────────


def test_request_creates_pending(store):
    cid = store.request_continuation("s1", "Finish auth refactor")
    assert cid
    assert store.pending_count() == 1


def test_request_stores_details(store):
    cid = store.request_continuation(
        "s1",
        "Finish auth refactor",
        stopping_point="auth.py:120",
        hints=["run tests first"],
    )
    pending = store.pending()
    assert len(pending) == 1
    entry = pending[0]
    assert entry["id"] == cid
    assert entry["task_summary"] == "Finish auth refactor"
    assert entry["stopping_point"] == "auth.py:120"
    assert entry["hints"] == ["run tests first"]
    assert entry["status"] == "pending"


def test_pending_newest_first(store):
    store.request_continuation("s1", "old task")
    cid2 = store.request_continuation("s2", "new task")
    pending = store.pending()
    assert pending[0]["id"] == cid2


def test_pending_limit(store):
    for i in range(7):
        store.request_continuation(f"s{i}", f"task {i}")
    assert len(store.pending(limit=5)) == 5


# ── resolving ──────────────────────────────────────────────────────


def test_resolve_completed(store):
    cid = store.request_continuation("s1", "task")
    assert store.resolve(cid, "completed") is True
    assert store.pending_count() == 0


def test_resolve_abandoned(store):
    cid = store.request_continuation("s1", "task")
    assert store.resolve(cid, "abandoned") is True
    assert store.pending_count() == 0


def test_resolve_unknown_id(store):
    assert store.resolve("ghost", "completed") is False


def test_resolve_rejects_pending_status(store):
    cid = store.request_continuation("s1", "task")
    assert store.resolve(cid, "pending") is False
    assert store.pending_count() == 1


# ── persistence ────────────────────────────────────────────────────


def test_persists_across_instances(tmp_path):
    s1 = ContinuationStore(home=tmp_path)
    s1.request_continuation("s1", "task")
    s2 = ContinuationStore(home=tmp_path)
    assert s2.pending_count() == 1


def test_snapshot_shape(store):
    store.request_continuation("s1", "task")
    snap = store.snapshot()
    assert "continuations" in snap
