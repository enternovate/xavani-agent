# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Concurrent tool-batch heuristics (backlog D79).

Covers the parallel/serial decision rule and the executor guarantees:
read-only batches run in parallel, mixed batches serialize writes, and a
single failing tool never kills the batch.
"""

import json
import threading
import time
from unittest.mock import MagicMock

import run_agent as _ra
from agent.tool_dispatch_helpers import _should_parallelize_tool_batch


class _FakeToolCall:
    def __init__(self, name, args="{}", call_id="tc_1"):
        self.function = MagicMock(name=name, arguments=args)
        self.function.name = name
        self.id = call_id


class _FakeAssistantMsg:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


def _batch(*tool_calls):
    return list(tool_calls)


def _msg(*tool_calls):
    return _FakeAssistantMsg(list(tool_calls))


def _read_call(path):
    return _FakeToolCall("read_file", json.dumps({"path": path}))


def _write_call(path):
    return _FakeToolCall("write_file", json.dumps({"path": path}))


class TestParallelizeHeuristic:
    def test_read_only_batch_on_disjoint_paths_parallelizes(self):
        assert _should_parallelize_tool_batch(_batch(_read_call("/a"), _read_call("/b")))

    def test_read_only_batch_on_same_path_serializes(self):
        assert not _should_parallelize_tool_batch(_batch(_read_call("/a"), _read_call("/a")))

    def test_mixed_read_write_on_same_path_serializes(self):
        assert not _should_parallelize_tool_batch(_batch(_read_call("/a"), _write_call("/a")))

    def test_mixed_read_write_on_disjoint_paths_parallelizes(self):
        assert _should_parallelize_tool_batch(_batch(_read_call("/a"), _write_call("/b")))

    def test_two_writes_on_same_path_serialize(self):
        assert not _should_parallelize_tool_batch(_batch(_write_call("/a"), _write_call("/a")))

    def test_two_writes_on_disjoint_paths_parallelize(self):
        assert _should_parallelize_tool_batch(_batch(_write_call("/a"), _write_call("/b")))

    def test_batch_with_mutating_memory_tool_serializes(self):
        calls = _batch(_read_call("/a"), _FakeToolCall("memory", '{"action": "add"}'))
        assert not _should_parallelize_tool_batch(calls)

    def test_batch_with_terminal_serializes(self):
        calls = _batch(_read_call("/a"), _FakeToolCall("terminal", '{"command": "ls"}'))
        assert not _should_parallelize_tool_batch(calls)

    def test_batch_with_unknown_tool_serializes_fail_closed(self):
        calls = _batch(_read_call("/a"), _FakeToolCall("brand_new_tool_xyz", "{}"))
        assert not _should_parallelize_tool_batch(calls)

    def test_single_call_serializes(self):
        assert not _should_parallelize_tool_batch(_batch(_read_call("/a")))

    def test_deferred_meta_tools_are_parallel_safe(self):
        calls = _batch(_FakeToolCall("tool_search", '{"query": "x"}'),
                       _FakeToolCall("tool_describe", '{"name": "x"}'))
        assert _should_parallelize_tool_batch(calls)


class _StubAgent:
    _interrupt_requested = False
    _interrupt_message = None
    _execution_thread_id = threading.current_thread().ident
    _interrupt_thread_signal_pending = False
    log_prefix = ""
    quiet_mode = True
    verbose_logging = False
    log_prefix_chars = 200
    _checkpoint_mgr = MagicMock(enabled=False)
    _subdirectory_hints = MagicMock(check_tool_call=MagicMock(return_value=""))
    tool_progress_callback = None
    tool_start_callback = None
    tool_complete_callback = None
    _todo_store = MagicMock()
    _session_db = None
    valid_tool_names = set()
    _turns_since_memory = 0
    _iters_since_skill = 0
    _current_tool = None
    _last_activity = 0
    _print_fn = print
    _active_children = []
    _tool_guardrails = MagicMock(
        before_call=MagicMock(return_value=MagicMock(allows_execution=True))
    )

    def __init__(self):
        self._tool_worker_threads = set()
        self._tool_worker_threads_lock = threading.Lock()
        self._active_children_lock = threading.Lock()
        self._max_concurrent = 0
        self._active_count = 0
        self._count_lock = threading.Lock()

    def _touch_activity(self, desc):
        self._last_activity = time.time()

    def _vprint(self, msg, force=False):
        pass

    def _safe_print(self, msg):
        pass

    def _should_emit_quiet_tool_messages(self):
        return False

    def _should_start_quiet_spinner(self):
        return False

    def _has_stream_consumers(self):
        return False

    def _apply_pending_steer_to_tool_results(self, *a, **kw):
        pass

    def _append_guardrail_observation(self, tool_name, function_args, function_result, *, failed):
        return function_result

    def _tool_result_content_for_active_model(self, name, result):
        return result

    def _invoke_tool(self, name, args, task_id, call_id, **kw):
        with self._count_lock:
            self._active_count += 1
            self._max_concurrent = max(self._max_concurrent, self._active_count)
        time.sleep(0.05)
        with self._count_lock:
            self._active_count -= 1
        return json.dumps({"ok": name})


def _make_stub():
    stub = _StubAgent()
    stub._execute_tool_calls_concurrent = _ra.AIAgent._execute_tool_calls_concurrent.__get__(stub)
    stub._invoke_tool = stub._invoke_tool
    return stub


class TestExecutorParallelism:
    def test_read_only_batch_runs_in_parallel(self):
        stub = _make_stub()
        msg = _msg(_read_call("/a"), _read_call("/b"), _read_call("/c"))

        stub._execute_tool_calls_concurrent(msg, [], "task")

        assert stub._max_concurrent >= 2

    def test_single_failure_does_not_kill_batch(self):
        stub = _make_stub()

        def _flaky(name, args, task_id, call_id, **kw):
            if name == "read_file":
                raise RuntimeError("boom")
            return json.dumps({"ok": name})

        stub._invoke_tool = _flaky
        messages = []
        msg = _msg(_read_call("/a"), _FakeToolCall("web_search", "{}"))

        stub._execute_tool_calls_concurrent(msg, messages, "task")

        assert len(messages) == 2
        results = [m["content"] for m in messages]
        assert any("Error executing tool 'read_file'" in r for r in results)
        assert any('"ok": "web_search"' in r for r in results)
