"""Focused tests for the hung API-call watchdog."""

from __future__ import annotations

import threading
import time

import pytest

from agent import chat_completion_helpers
from agent.api_call_watchdog import ApiCallWatchdog


def test_default_threshold_is_120_seconds():
    watchdog = ApiCallWatchdog(lambda _message: None)

    assert watchdog.threshold_seconds == 120.0


def test_warning_fires_at_threshold():
    warnings: list[str] = []
    warned = threading.Event()

    def record_warning(message: str) -> None:
        warnings.append(message)
        warned.set()

    watchdog = ApiCallWatchdog(record_warning, threshold_seconds=0.05)
    watchdog.start()
    try:
        assert warned.wait(timeout=1.0)
        assert len(warnings) == 1
        assert "API call" in warnings[0]
        assert "0.05" in warnings[0]
    finally:
        watchdog.stop()


def test_no_warning_before_threshold():
    warnings: list[str] = []
    watchdog = ApiCallWatchdog(warnings.append, threshold_seconds=0.2)
    watchdog.start()
    try:
        time.sleep(0.03)
        assert warnings == []
    finally:
        watchdog.stop()


def test_concurrent_start_does_not_create_duplicate_threads(monkeypatch):
    watchdog = ApiCallWatchdog(lambda _message: None, threshold_seconds=10.0)
    original_start = threading.Thread.start
    first_start_entered = threading.Event()
    second_start_entered = threading.Event()
    release_first_start = threading.Event()
    start_calls = 0
    start_lock = threading.Lock()

    def delayed_start(thread):
        nonlocal start_calls
        if thread.name != "api-call-watchdog":
            original_start(thread)
            return
        with start_lock:
            start_calls += 1
            call_number = start_calls
        if call_number == 1:
            first_start_entered.set()
            release_first_start.wait(timeout=1.0)
        else:
            second_start_entered.set()
        original_start(thread)

    monkeypatch.setattr(threading.Thread, "start", delayed_start)
    first = threading.Thread(target=watchdog.start)
    second = threading.Thread(target=watchdog.start)
    try:
        original_start(first)
        assert first_start_entered.wait(timeout=1.0)
        original_start(second)
        assert second_start_entered.wait(timeout=0.5) is False
        release_first_start.set()
        first.join(timeout=1.0)
        second.join(timeout=1.0)

        assert start_calls == 1
    finally:
        release_first_start.set()
        first.join(timeout=1.0)
        second.join(timeout=1.0)
        watchdog.stop()


def test_stop_retains_blocked_callback_thread_reference():
    callback_started = threading.Event()
    release_callback = threading.Event()

    def blocking_callback(_message: str) -> None:
        callback_started.set()
        release_callback.wait(timeout=3.0)

    watchdog = ApiCallWatchdog(blocking_callback, threshold_seconds=0.05)
    watchdog.start()
    try:
        assert callback_started.wait(timeout=1.0)
        callback_thread = watchdog._thread
        watchdog.stop()

        assert callback_thread is not None
        assert callback_thread.is_alive()
        assert watchdog._thread is callback_thread
    finally:
        release_callback.set()
        watchdog.stop()


def test_start_refuses_restart_while_callback_thread_is_alive():
    callback_started = threading.Event()
    release_callback = threading.Event()

    def blocking_callback(_message: str) -> None:
        callback_started.set()
        release_callback.wait(timeout=3.0)

    watchdog = ApiCallWatchdog(blocking_callback, threshold_seconds=0.05)
    watchdog.start()
    try:
        assert callback_started.wait(timeout=1.0)
        callback_thread = watchdog._thread
        watchdog.stop()
        watchdog.start()

        assert watchdog._thread is callback_thread
        assert watchdog.is_running is True
    finally:
        release_callback.set()
        watchdog.stop()


def test_stop_keeps_blocked_watchdog_tracked_during_restart():
    callback_started = threading.Event()
    release_callback = threading.Event()
    second_callback_started = threading.Event()
    callback_count = 0
    callback_lock = threading.Lock()

    def blocking_callback(_message: str) -> None:
        nonlocal callback_count
        with callback_lock:
            callback_count += 1
            if callback_count > 1:
                second_callback_started.set()
        callback_started.set()
        release_callback.wait(timeout=3.0)

    watchdog = ApiCallWatchdog(blocking_callback, threshold_seconds=0.05)
    watchdog.start()
    try:
        assert callback_started.wait(timeout=1.0)
        watchdog.stop()
        watchdog.start()

        assert watchdog.is_running is True
        assert second_callback_started.wait(timeout=0.2) is False
        with callback_lock:
            assert callback_count == 1
    finally:
        release_callback.set()
        watchdog.stop()


def test_stop_cleans_up_pending_warning():
    warnings: list[str] = []
    watchdog = ApiCallWatchdog(warnings.append, threshold_seconds=0.05)

    watchdog.start()
    watchdog.stop()
    time.sleep(0.1)

    assert warnings == []
    assert watchdog.is_running is False


def test_callback_failure_does_not_escape_watchdog_thread(caplog):
    callback_finished = threading.Event()

    def broken_callback(_message: str) -> None:
        callback_finished.set()
        raise RuntimeError("status sink failed")

    watchdog = ApiCallWatchdog(broken_callback, threshold_seconds=0.05)
    watchdog.start()
    try:
        assert callback_finished.wait(timeout=1.0)
        time.sleep(0.1)
        assert "status sink failed" in caplog.text
    finally:
        watchdog.stop()


def test_unexpected_polling_exception_stops_watchdog(monkeypatch):
    release_api_call = threading.Event()
    watchdogs = []

    class RecordingWatchdog:
        def __init__(self, _callback, *, threshold_seconds):
            self.started = False
            self.stopped = False
            watchdogs.append(self)

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    class Agent:
        api_mode = "anthropic_messages"
        api_call_watchdog_threshold = 120.0

        @property
        def _interrupt_requested(self):
            raise RuntimeError("polling failed")

        def _compute_non_stream_stale_timeout(self, _messages):
            return 10.0

        def _touch_activity(self, _message):
            return None

        def _anthropic_messages_create(self, _api_kwargs):
            release_api_call.wait(timeout=2.0)
            return object()

    monkeypatch.setattr(chat_completion_helpers, "ApiCallWatchdog", RecordingWatchdog)
    try:
        with pytest.raises(RuntimeError, match="polling failed"):
            chat_completion_helpers.interruptible_api_call(Agent(), {})
    finally:
        release_api_call.set()

    assert len(watchdogs) == 1
    assert watchdogs[0].started is True
    assert watchdogs[0].stopped is True


@pytest.mark.parametrize("threshold", [0, -1, float("nan")])
def test_non_positive_or_nan_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        ApiCallWatchdog(lambda _message: None, threshold_seconds=threshold)
