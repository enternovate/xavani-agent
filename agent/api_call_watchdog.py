"""Warn when an API call exceeds its inactivity threshold."""

from __future__ import annotations

import logging
import math
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

DEFAULT_API_CALL_WATCHDOG_SECONDS = 120.0


class ApiCallWatchdog:
    """Run one warning callback when an API call stays active too long."""

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

    @property
    def is_running(self) -> bool:
        """Return True while the watchdog thread runs."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the watchdog thread once."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="api-call-watchdog",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the watchdog thread and wait for cleanup."""
        self._stop_event.set()
        thread = self._thread
        if thread is None or thread is threading.current_thread():
            return
        thread.join(timeout=1.0)
        if not thread.is_alive():
            self._thread = None

    def _run(self) -> None:
        if self._stop_event.wait(self.threshold_seconds):
            return
        try:
            self.warning_callback(
                f"API call has no response after {self.threshold_seconds:g}s."
            )
        except Exception as exc:
            logger.error("API call watchdog warning callback failed: %s", exc, exc_info=True)
