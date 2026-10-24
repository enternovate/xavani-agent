#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""TDD tests for task-scoped hashline snapshot provenance (R1 Task 07).

Hashline snapshots are per-TASK observations: two subagents running
concurrently must not be able to authorize an edit from each other's reads,
so ``TaskSnapshotStores`` mints one ``SnapshotStore`` per explicit task
identity, refuses the anonymous ``'default'`` identity, and bounds the
registry with an LRU cap so a long-lived process cannot grow forever.
"""

import threading

import pytest

from tools.hashline.snapshots import (
    DEFAULT_MAX_TASKS,
    SnapshotStore,
    TaskSnapshotStores,
    compute_tag,
    task_stores,
)


def test_task_stores_get_returns_a_snapshot_store():
    stores = TaskSnapshotStores()
    assert isinstance(stores.for_task("task-a"), SnapshotStore)


def test_two_tasks_do_not_share_observed_ranges():
    """A snapshot recorded by one task is invisible to another task."""
    stores = TaskSnapshotStores()
    a = stores.for_task("task-a")
    b = stores.for_task("task-b")

    assert a is not b
    assert a.record("/repo/one.py", "a\nb\nc\n", ranges=((1, 2),)) == compute_tag("a\nb\nc\n")
    assert a.get("/repo/one.py") is not None
    assert b.get("/repo/one.py") is None


def test_same_task_sees_its_own_observations():
    stores = TaskSnapshotStores()
    stores.for_task("task-a").record("/repo/one.py", "a\n", ranges=((1, 1),))
    assert stores.for_task("task-a").get("/repo/one.py") is not None


@pytest.mark.parametrize("bad", [None, "", "   ", "\t", "default", " default "])
def test_for_task_rejects_missing_blank_or_default(bad):
    stores = TaskSnapshotStores()
    with pytest.raises(ValueError):
        stores.for_task(bad)


def test_for_task_error_names_the_contract():
    stores = TaskSnapshotStores()
    with pytest.raises(ValueError, match="task"):
        stores.for_task("default")


def test_discard_removes_the_task_store():
    stores = TaskSnapshotStores()
    stores.for_task("task-a").record("/repo/one.py", "a\n", ranges=((1, 1),))
    assert len(stores) == 1

    stores.discard("task-a")

    assert len(stores) == 0
    # A fresh store for the same id starts empty (no resurrected snapshots).
    assert stores.for_task("task-a").get("/repo/one.py") is None


def test_discard_of_unknown_task_is_a_noop():
    stores = TaskSnapshotStores()
    stores.discard("never-seen")
    assert len(stores) == 0


def test_lru_cap_evicts_the_oldest_task():
    stores = TaskSnapshotStores(max_tasks=2)
    stores.for_task("task-1").record("/repo/one.py", "a\n", ranges=((1, 1),))
    stores.for_task("task-2")

    stores.for_task("task-3")  # evicts task-1

    assert len(stores) == 2
    assert stores.for_task("task-1").get("/repo/one.py") is None


def test_lru_cap_keeps_the_most_recently_used_task():
    stores = TaskSnapshotStores(max_tasks=2)
    stores.for_task("task-1").record("/repo/one.py", "a\n", ranges=((1, 1),))
    stores.for_task("task-2")
    stores.for_task("task-1")  # refresh recency

    stores.for_task("task-3")  # evicts task-2 instead

    assert stores.for_task("task-1").get("/repo/one.py") is not None


def test_module_singleton_is_capped_at_32_tasks():
    assert DEFAULT_MAX_TASKS == 32
    for i in range(DEFAULT_MAX_TASKS):
        task_stores.for_task(f"cap-probe-{i}").record("/repo/cap.py", "a\n", ranges=((1, 1),))

    task_stores.for_task("cap-probe-final")  # evicts the oldest probe

    assert len(task_stores) <= DEFAULT_MAX_TASKS
    assert task_stores.for_task("cap-probe-0").get("/repo/cap.py") is None
    task_stores.discard("cap-probe-final")


# ---------------------------------------------------------------------------
# Cleanup: a finished subagent's store is discarded (not just LRU-evicted)
# ---------------------------------------------------------------------------


class _StubChild:
    """Minimal AIAgent stand-in for the delegate_tool cleanup path."""

    _subagent_id = "sa-cleanup-probe"
    _delegate_depth = 1
    _delegate_role = "leaf"
    model = "test/model"
    provider = "testprov"
    api_mode = "chat_completions"
    base_url = "https://example.test/v1"
    max_iterations = 5
    quiet_mode = True
    skip_memory = True
    skip_context_files = True
    platform = "cli"
    ephemeral_system_prompt = "sys"
    enabled_toolsets = ["file"]
    valid_tool_names = {"read_file"}
    tools = [{"name": "read_file", "description": "read"}]
    verbose_logging = False
    _delegate_saved_tool_names = ["read_file"]

    def run_conversation(self, user_message, task_id=None):
        return {"final_response": "done", "completed": True, "api_calls": 1}

    def get_activity_summary(self):
        return {
            "api_call_count": 1,
            "max_iterations": self.max_iterations,
            "current_tool": None,
            "seconds_since_activity": 1,
        }

    def interrupt(self):
        pass

    def close(self):
        pass


class _StubParent:
    _current_task_id = None
    _subagent_id = None
    verbose_logging = False

    def __init__(self):
        self._active_children = []
        self._active_children_lock = threading.Lock()

    def _touch_activity(self):
        pass

    def _vprint(self, *a, **kw):
        pass


def test_finished_subagent_store_is_discarded(monkeypatch, tmp_path):
    """The delegate_tool finally block frees the child's task-scoped store."""
    from tools import delegate_tool

    monkeypatch.setenv("XAVANI_HOME", str(tmp_path / ".xavani"))
    task_id = _StubChild._subagent_id
    task_stores.for_task(task_id).record("/repo/x.py", "a\n", ranges=((1, 1),))
    assert task_id in task_stores

    result = delegate_tool._run_single_child(
        task_index=9, goal="cleanup probe", child=_StubChild(), parent_agent=_StubParent()
    )

    assert result["status"] == "completed", result
    assert task_id not in task_stores
    assert task_stores.for_task(task_id).get("/repo/x.py") is None
