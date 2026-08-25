"""Adaptive stream pacing for the CLI (TDD module).

Batches token deltas into time-boxed windows so a fast provider does not
flood the terminal with one print per token. The window inflates after a
slow flush (adaptive backpressure, capped) and shrinks back to the floor,
mirroring how game renderers hold a stable frame budget.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable

# ~60fps target: minimum gap between display flushes.
MIN_FLUSH_INTERVAL_S = 1 / 60

# Adaptive ceiling: never stall output longer than this, even after a
# pathological slow frame (huge transcript line, terminal lag).
MAX_ADAPTIVE_INTERVAL_S = 0.2


class StreamScheduler:
    """Time-boxed batcher for streamed text deltas.

    ``flush(text)`` receives whatever accumulated since the last flush.
    Callers feed ``submit()`` per delta; the scheduler decides when to
    hand text to the display.
    """

    def __init__(
        self,
        flush: Callable[[str], None],
        clock: Callable[[], float] = time.monotonic,
        min_interval: float = MIN_FLUSH_INTERVAL_S,
        max_adaptive: float = MAX_ADAPTIVE_INTERVAL_S,
    ) -> None:
        self._flush_fn = flush
        self._clock = clock
        self.min_interval = min_interval
        self.max_adaptive = max_adaptive
        self._buf: list[str] = []
        self._buf_len = 0
        self._last_flush_at: float | None = None
        self._last_frame_cost = 0.0
        # 30-frame rolling window of inter-flush gaps, for fps readout.
        self._gaps: deque[float] = deque(maxlen=30)
        self.total_flushes = 0

    def submit(self, text: str) -> None:
        """Buffer one delta; flush when the current window has elapsed."""
        if not text:
            return
        now = self._clock()
        if self._last_flush_at is None:
            # First delta of the stream: emit immediately so latency to
            # first paint stays minimal.
            self._flush_now(text, now)
            return
        self._buf.append(text)
        self._buf_len += len(text)
        elapsed = now - self._last_flush_at
        if elapsed >= self._current_interval():
            self._drain(now)

    def finish(self) -> None:
        """Flush any buffered remainder (call at stream end)."""
        if not self._buf:
            return
        self._drain(self._clock())

    def boost(self) -> None:
        """Drop adaptive delay (user is scrolling/typing — stay responsive)."""
        self._last_frame_cost = 0.0

    def _current_interval(self) -> float:
        adaptive = min(self.max_adaptive, self._last_frame_cost * 2)
        return max(self.min_interval, adaptive)

    def _drain(self, now: float) -> None:
        text = "".join(self._buf)
        self._buf.clear()
        self._buf_len = 0
        start = now
        self._flush_fn(text)
        end = self._clock()
        if self._last_flush_at is not None:
            self._gaps.append(start - self._last_flush_at)
        self._last_flush_at = end
        self._last_frame_cost = end - start
        self.total_flushes += 1

    def _flush_now(self, text: str, now: float) -> None:
        start = now
        self._flush_fn(text)
        end = self._clock()
        if self._last_flush_at is not None:
            self._gaps.append(start - self._last_flush_at)
        self._last_flush_at = end
        self._last_frame_cost = end - start
        self.total_flushes += 1

    @property
    def fps(self) -> float:
        """Rolling flush rate over the last 30 windows (0 until warm)."""
        if len(self._gaps) < 2:
            return 0.0
        span = sum(self._gaps)
        if span <= 0:
            return 0.0
        return round((len(self._gaps) - 1) / span, 1)

    @property
    def pending_chars(self) -> int:
        return self._buf_len
