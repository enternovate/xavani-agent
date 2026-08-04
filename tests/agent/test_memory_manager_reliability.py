# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Reliability tests for MemoryManager background-executor machinery.

Covers the Hermes-ported reliability surface:

* ``_submit_background`` / ``_get_sync_executor`` — background writes on a
  named, daemon ``xavani-memory-*`` thread pool,
* ``flush_pending`` — bounded barrier that drains queued background work,
* ``commit_session_boundary_async`` — end→switch ordering on the worker,
* ``notify_memory_tool_write`` — mirrors ONLY succeeded add/replace/remove,
* ``shutdown_drain_state`` — pending-count snapshot after a bounded drain.

All tests are hermetic: no network, no provider plugins, no XAVANI_HOME.
"""

import json
import threading
import time

from agent.memory_manager import MemoryManager
from agent.memory_provider import MemoryProvider


class _RecordingProvider(MemoryProvider):
    """Minimal provider that records every hook invocation."""

    def __init__(self, name="external"):
        self._name = name
        self.synced_turns = []
        self.memory_writes = []
        self.session_end_calls = []
        self.switch_calls = []
        self.shutdown_called = False

    @property
    def name(self):
        return self._name

    def is_available(self):
        return True

    def initialize(self, session_id, **kwargs):
        pass

    def get_tool_schemas(self):
        return []

    def sync_turn(self, user_content, assistant_content, *, session_id=""):
        self.synced_turns.append((user_content, assistant_content, session_id))

    def handle_tool_call(self, tool_name, args, **kwargs):
        return "{}"

    def on_session_end(self, messages):
        self.session_end_calls.append(list(messages))

    def on_session_switch(self, new_session_id, *, parent_session_id="", reset=False, **kwargs):
        self.switch_calls.append(
            {"new": new_session_id, "parent": parent_session_id, "reset": reset, "extra": kwargs}
        )

    def on_memory_write(self, action, target, content, metadata=None):
        self.memory_writes.append((action, target, content, dict(metadata or {})))

    def shutdown(self):
        self.shutdown_called = True


def _manager_with(provider):
    mgr = MemoryManager()
    mgr.add_provider(_RecordingProvider(name="builtin"))
    mgr.add_provider(provider)
    return mgr


# ---------------------------------------------------------------------------
# flush_pending
# ---------------------------------------------------------------------------


class TestFlushPending:
    def test_flush_pending_drains_background_write(self):
        """A background write submitted via _submit_background lands after
        flush_pending returns True."""
        provider = _RecordingProvider()
        mgr = _manager_with(provider)

        def _background_write():
            provider.sync_turn("user", "assistant", session_id="sess-1")

        mgr._submit_background(_background_write, kind="write")

        # The work is queued on the executor (or already done) — flushing must
        # observe it regardless.
        assert mgr.flush_pending(timeout=5) is True
        assert provider.synced_turns == [("user", "assistant", "sess-1")]

    def test_flush_pending_returns_true_when_no_executor(self):
        """No background executor ever created → nothing pending → True."""
        mgr = MemoryManager()
        assert mgr.flush_pending(timeout=0.01) is True

    def test_flush_pending_times_out_on_wedged_task(self):
        """A task that never completes makes flush_pending return False,
        not block forever."""
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        release = threading.Event()

        def _wedged():
            release.wait(30)  # held until the test releases it

        # Occupy BOTH workers with wedged tasks — otherwise the flush sentinel
        # can complete on the second worker and mask the timeout.
        mgr._submit_background(_wedged, kind="write")
        mgr._submit_background(_wedged, kind="write")
        assert mgr.flush_pending(timeout=0.1) is False

        # Unblock and verify the drain completes once the tasks finish.
        release.set()
        assert mgr.flush_pending(timeout=5) is True

    def test_background_executor_uses_named_daemon_threads(self):
        """Workers are named xavani-memory-* and daemon (never block exit)."""
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        seen = {}

        def _record():
            t = threading.current_thread()
            seen["name"] = t.name
            seen["daemon"] = t.daemon

        mgr._submit_background(_record, kind="write")
        assert mgr.flush_pending(timeout=5) is True
        assert seen["name"].startswith("xavani-memory-")
        assert seen["daemon"] is True


# ---------------------------------------------------------------------------
# commit_session_boundary_async
# ---------------------------------------------------------------------------


class TestCommitSessionBoundaryAsync:
    def test_boundary_commits_end_then_switch_in_order(self):
        """on_session_end must land strictly before on_session_switch."""
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        order = []

        def _track_end(messages):
            order.append("end")

        def _track_switch(*args, **kwargs):
            order.append("switch")

        provider.on_session_end = _track_end
        provider.on_session_switch = _track_switch

        messages = [{"role": "user", "content": "hi"}]
        mgr.commit_session_boundary_async(
            messages,
            new_session_id="sess-2",
            parent_session_id="sess-1",
            reason="new_session",
        )
        assert mgr.flush_pending(timeout=5) is True
        assert order == ["end", "switch"]

    def test_boundary_skips_when_no_providers(self):
        """No providers → no background task, flush stays trivially true."""
        mgr = MemoryManager()
        mgr.commit_session_boundary_async([], new_session_id="sess-2")
        assert mgr.flush_pending(timeout=5) is True

    def test_boundary_after_shutdown_rejected_not_run(self):
        """Submitting a boundary after shutdown_all must not execute."""
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.shutdown_all()
        mgr.commit_session_boundary_async([], new_session_id="sess-2")
        assert provider.session_end_calls == []
        assert provider.switch_calls == []


# ---------------------------------------------------------------------------
# notify_memory_tool_write
# ---------------------------------------------------------------------------


class TestNotifyMemoryToolWrite:
    def test_mirrors_succeeded_single_add(self):
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            {"success": True, "staged": False},
            {"action": "add", "target": "memory", "content": "prefers dark mode"},
        )
        assert provider.memory_writes == [
            ("add", "memory", "prefers dark mode", {})
        ]

    def test_skips_failed_result(self):
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            {"success": False, "error": "nope"},
            {"action": "add", "content": "x"},
        )
        assert provider.memory_writes == []

    def test_skips_staged_for_approval_write(self):
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            {"success": True, "staged": True},
            {"action": "add", "content": "pending approval"},
        )
        assert provider.memory_writes == []

    def test_skips_non_json_string_result(self):
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            "not json at all",
            {"action": "add", "content": "x"},
        )
        assert provider.memory_writes == []

    def test_accepts_json_string_result(self):
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            json.dumps({"success": True, "staged": False}),
            {"action": "add", "content": "from json string"},
        )
        assert provider.memory_writes == [("add", "memory", "from json string", {})]

    def test_batch_mirrors_only_mutating_actions(self):
        """Batched operations expand; only add/replace/remove are mirrored."""
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            {"success": True},
            {
                "target": "user",
                "operations": [
                    {"action": "add", "content": "one"},
                    {"action": "replace", "content": "two", "old_text": "one"},
                    {"action": "remove", "content": "three"},
                    {"action": "recall", "content": "not a write"},
                    {"action": "add"},  # no content → mirrored with ""
                ],
            },
        )
        assert provider.memory_writes == [
            ("add", "user", "one", {}),
            ("replace", "user", "two", {"old_text": "one"}),
            ("remove", "user", "three", {}),
            ("add", "user", "", {}),
        ]

    def test_build_metadata_callable_attaches_provenance(self):
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.notify_memory_tool_write(
            {"success": True},
            {"action": "replace", "target": "memory", "content": "new", "old_text": "old"},
            build_metadata=lambda: {"task_id": "task-9", "tool_call_id": "call-1"},
        )
        assert provider.memory_writes == [
            ("replace", "memory", "new", {"task_id": "task-9", "tool_call_id": "call-1", "old_text": "old"})
        ]

    def test_builtin_provider_never_receives_mirror(self):
        """Mirrors skip the builtin provider (it is the write's source)."""
        builtin = _RecordingProvider(name="builtin")
        ext = _RecordingProvider(name="ext")
        mgr = MemoryManager()
        mgr.add_provider(builtin)
        mgr.add_provider(ext)
        mgr.notify_memory_tool_write(
            {"success": True},
            {"action": "add", "content": "x"},
        )
        assert builtin.memory_writes == []
        assert ext.memory_writes == [("add", "memory", "x", {})]


# ---------------------------------------------------------------------------
# shutdown_drain_state
# ---------------------------------------------------------------------------


class TestShutdownDrainState:
    def test_drain_state_drained_when_no_background_work(self, monkeypatch):
        """No executor ever created → drain is a no-op reporting 'drained'."""
        monkeypatch.setattr("agent.memory_manager._SYNC_DRAIN_TIMEOUT_S", 0.1)
        mgr = MemoryManager()
        mgr.shutdown_all()
        state = mgr.shutdown_drain_state
        assert state["status"] == "drained"
        assert state["abandoned_writes"] == 0
        assert state["abandoned_prefetches"] == 0
        assert state["active_tasks"] == 0

    def test_drain_state_counts_pending_and_abandoned(self, monkeypatch):
        """A wedged running task + queued write/prefetch tasks are counted:
        running tasks are active, queued ones are abandoned by class."""
        monkeypatch.setattr("agent.memory_manager._SYNC_DRAIN_TIMEOUT_S", 0.2)
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        release = threading.Event()
        started = []
        started_lock = threading.Lock()

        def _blocked(name):
            with started_lock:
                started.append(name)
            release.wait(30)

        def _wait_started(count):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with started_lock:
                    if len(started) >= count:
                        return
                time.sleep(0.01)
            raise AssertionError(f"only {len(started)}/{count} workers started")

        # Occupy BOTH workers with tasks that never finish on their own…
        mgr._submit_background(lambda: _blocked("w1"), kind="write")
        mgr._submit_background(lambda: _blocked("w2"), kind="write")
        _wait_started(2)
        # …then queue one write and one prefetch behind them (both cancelable).
        mgr._submit_background(lambda: None, kind="write")
        mgr._submit_background(lambda: None, kind="prefetch")

        mgr.shutdown_all()
        state = mgr.shutdown_drain_state
        assert state["status"] == "timed_out"
        assert state["abandoned_writes"] == 1
        assert state["abandoned_prefetches"] == 1
        assert state["active_tasks"] == 2

        # A wedged provider must never block the test process.
        release.set()

    def test_drain_state_drained_after_background_work_completes(self, monkeypatch):
        """All background work finished → drain reports 'drained', zero counts."""
        monkeypatch.setattr("agent.memory_manager._SYNC_DRAIN_TIMEOUT_S", 0.2)
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr._submit_background(
            lambda: provider.sync_turn("u", "a", session_id="s"),
            kind="write",
        )
        # Let the task finish before draining.
        assert mgr.flush_pending(timeout=5) is True
        mgr.shutdown_all()
        state = mgr.shutdown_drain_state
        assert state["status"] == "drained"
        assert state["abandoned_writes"] == 0
        assert state["abandoned_prefetches"] == 0
        assert state["active_tasks"] == 0
        assert provider.synced_turns == [("u", "a", "s")]

    def test_shutdown_all_rejects_late_background_submissions(self, monkeypatch):
        """After shutdown, _submit_background drops tasks instead of running them."""
        monkeypatch.setattr("agent.memory_manager._SYNC_DRAIN_TIMEOUT_S", 0.1)
        provider = _RecordingProvider()
        mgr = _manager_with(provider)
        mgr.shutdown_all()
        ran = []

        mgr._submit_background(lambda: ran.append(1), kind="write")
        assert ran == []
        assert mgr.flush_pending(timeout=0.1) is True  # executor gone → trivially drained
