"""Tests for xavani_cli.stream_scheduler."""

from xavani_cli.stream_scheduler import StreamScheduler


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _make(interval_s=1 / 60):
    clock = FakeClock()
    flushed: list[str] = []
    sched = StreamScheduler(
        flush=flushed.append,
        clock=clock,
        min_interval=interval_s,
        max_adaptive=0.2,
    )
    return sched, clock, flushed


class TestBatching:
    def test_first_delta_flushes_immediately(self):
        sched, _, flushed = _make()
        sched.submit("hello")
        assert flushed == ["hello"]

    def test_rapid_deltas_batch_into_one_flush(self):
        sched, clock, flushed = _make()
        sched.submit("a")
        clock.advance(0.001)
        sched.submit("b")
        clock.advance(0.001)
        sched.submit("c")  # still inside the 16ms window
        assert flushed == ["a"]
        assert sched.pending_chars == 2

    def test_window_elapse_drains_buffer(self):
        sched, clock, flushed = _make()
        sched.submit("a")
        clock.advance(0.02)
        sched.submit("b")
        assert flushed == ["a", "b"]

    def test_finish_drains_remainder(self):
        sched, _, flushed = _make()
        sched.submit("x")
        sched.finish()
        assert flushed[-1] == "x"
        assert sched.pending_chars == 0


class TestAdaptiveBackpressure:
    def test_slow_frame_inflates_next_window(self):
        # min_interval=10ms; flush itself costs 50ms → next window = 100ms.
        calls = []

        def slow_flush(text):
            calls.append(text)

        clock = FakeClock()
        sched = StreamScheduler(flush=slow_flush, clock=clock, min_interval=0.01, max_adaptive=0.2)

        def fake_flush_cost():
            clock.advance(0.05)

        # Wrap flush to charge the clock.
        slow_flush_wrapped = slow_flush
        orig = sched._flush_fn
        sched._flush_fn = lambda text: (orig(text), fake_flush_cost())

        sched.submit("1")  # immediate; cost 50ms recorded
        clock.advance(0.02)  # only 20ms since last flush — below adaptive floor (100ms)
        sched.submit("2")
        assert len(calls) == 1
        clock.advance(0.09)  # total 110ms > 100ms adaptive window
        sched.submit("3")
        assert len(calls) == 2

    def test_boost_resets_adaptive_delay(self):
        clock = FakeClock()
        calls = []
        sched = StreamScheduler(flush=calls.append, clock=clock, min_interval=0.01, max_adaptive=0.2)
        orig = sched._flush_fn
        sched._flush_fn = lambda text: (orig(text), clock.advance(0.05))
        sched.submit("1")
        sched.boost()  # user scrolled — drop the penalty
        clock.advance(0.02)
        sched.submit("2")
        assert len(calls) == 2


class TestFpsReadout:
    def test_fps_zero_until_warm(self):
        sched, _, _ = _make()
        assert sched.fps == 0.0

    def test_fps_counts_windows(self):
        sched, clock, _ = _make(interval_s=0.01)
        sched.submit("1")
        for _ in range(5):
            clock.advance(0.01)
            sched.submit("x")
        assert 0 < sched.fps <= 120.0
