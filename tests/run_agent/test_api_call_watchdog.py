"""Focused tests for the hung API-call watchdog."""

from __future__ import annotations

import threading
import time

import pytest

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


@pytest.mark.parametrize("threshold", [0, -1, float("nan")])
def test_non_positive_or_nan_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        ApiCallWatchdog(lambda _message: None, threshold_seconds=threshold)
