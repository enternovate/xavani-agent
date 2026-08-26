"""Warn when an API call exceeds its inactivity threshold."""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

DEFAULT_API_CALL_WATCHDOG_SECONDS = 120.0
WATCHDOG_STOP_TIMEOUT_SECONDS = 1.0


class ApiCallWatchdog:
    """Run one warning callback when an API call stays active too long.

    ``stop`` signals the watchdog and waits at most one second for its
    thread to exit.  Python cannot forcibly terminate a callback that is
    blocked in arbitrary user code, so a still-live callback thread remains
    tracked and a subsequent ``start`` is refused until it exits.
    """

    def __init__(
        self,
        warning_callback: Callable[[str], None],
        *,
        threshold_seconds: float = DEFAULT_API_CALL_WATCHDOG_SECONDS,
    ) -> None:
        threshold = float(threshold_seconds)
        if threshold <= 0 or not math.isfinite(threshold):
            raise ValueError("threshold_seconds must be a positive finite number")
        if not callable(warning_callback):
            raise TypeError("warning_callback must be callable")
        self.warning_callback = warning_callback
        self.threshold_seconds = threshold
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lifecycle_lock = threading.Lock()
        self._stopping = False

    @property
    def is_running(self) -> bool:
        """Return True while the watchdog thread runs."""
        with self._lifecycle_lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start one watchdog unless a previous thread is still alive."""
        with self._lifecycle_lock:
            if self._stopping:
                return
            if self._thread is not None:
                if self._thread.is_alive():
                    return
                self._thread = None
            self._stop_event.clear()
            thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="api-call-watchdog",
            )
            self._thread = thread
            thread.start()

    def stop(self) -> None:
        """Signal shutdown and wait at most one second for the thread.

        A callback that does not return within the bounded wait remains
        tracked.  It must finish before ``start`` can create a replacement.
        """
        with self._lifecycle_lock:
            if self._stopping:
                return
            self._stop_event.set()
            thread = self._thread
            if thread is None or thread is threading.current_thread():
                return
            self._stopping = True
        try:
            thread.join(timeout=WATCHDOG_STOP_TIMEOUT_SECONDS)
        finally:
            with self._lifecycle_lock:
                if not thread.is_alive() and self._thread is thread:
                    self._thread = None
                self._stopping = False

    def _run(self) -> None:
        if self._stop_event.wait(self.threshold_seconds):
            return
        try:
            self.warning_callback(
                f"API call has no response after {self.threshold_seconds:g}s."
            )
        except Exception as exc:
            logger.error("API call watchdog warning callback failed: %s", exc, exc_info=True)
