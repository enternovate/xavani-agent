# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Wiring tests for tool-call metrics."""

from __future__ import annotations

import inspect

from agent import tool_executor


class _FakeAgent:
    """Minimal agent stub with the attributes the metric helper reads."""

    def __init__(self) -> None:
        self.session_id = "wire-test-session"


def test_record_tool_metric_records_success(monkeypatch) -> None:
    """A successful call records a success row with latency and session id."""
    captured = []
    monkeypatch.setattr("agent.tool_metrics.record_call", captured.append)
    tool_executor._record_tool_metric(_FakeAgent(), "read_file", 100.0, 0.25, False)
    assert len(captured) == 1
    record = captured[0]
    assert record.tool == "read_file"
    assert record.latency_ms == 250.0
    assert record.success is True
    assert record.error_class == ""
    assert record.session_id == "wire-test-session"


def test_record_tool_metric_records_failure_with_error_class(monkeypatch) -> None:
    """A failed call records success False and the exception class name."""
    captured = []
    monkeypatch.setattr("agent.tool_metrics.record_call", captured.append)
    tool_executor._record_tool_metric(_FakeAgent(), "terminal", 200.0, 1.5, True, "TimeoutError")
    record = captured[0]
    assert record.success is False
    assert record.error_class == "TimeoutError"
    assert record.latency_ms == 1500.0


def test_record_tool_metric_never_raises(monkeypatch) -> None:
    """A broken metrics store must never break tool execution."""
    def _boom(*args, **kwargs):
        raise RuntimeError("metrics broken")

    monkeypatch.setattr("agent.tool_metrics.record_call", _boom)
    tool_executor._record_tool_metric(_FakeAgent(), "read_file", 0.0, 0.0, False)


def test_record_tool_metric_handles_missing_session_id(monkeypatch) -> None:
    """An agent without a session id still records a row."""
    captured = []
    monkeypatch.setattr("agent.tool_metrics.record_call", captured.append)
    tool_executor._record_tool_metric(object(), "read_file", 0.0, 0.0, False)
    assert captured[0].session_id == ""


def test_both_executors_call_the_metric_hook() -> None:
    """Contract: both dispatch paths record a metric per tool call.

    The concurrent path records inside the worker after execution; the
    sequential path records in the shared tail after failure detection.
    """
    concurrent_src = inspect.getsource(tool_executor.execute_tool_calls_concurrent)
    sequential_src = inspect.getsource(tool_executor.execute_tool_calls_sequential)
    assert "_record_tool_metric(" in concurrent_src
    assert "_record_tool_metric(" in sequential_src
