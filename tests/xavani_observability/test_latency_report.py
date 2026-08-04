# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C04: latency comparison report tests."""

import pytest

from xavani_observability.latency_report import (
    MIN_CALLS_FOR_RANKING,
    _median,
    _p95,
    build_latency_report,
    format_latency_report,
)
from xavani_observability.metrics import MetricsCollector


@pytest.fixture
def collector():
    return MetricsCollector(persist_path=None)


# ── percentile helpers ──────────────────────────────────────────────


def test_median_odd():
    assert _median([10, 20, 30]) == 20.0


def test_median_even():
    assert _median([10, 20, 30, 40]) == 25.0


def test_median_empty():
    assert _median([]) == 0.0


def test_p95_basic():
    values = [float(i) for i in range(100)]  # 0..99
    assert _p95(values) == 95


def test_p95_empty():
    assert _p95([]) == 0.0


# ── report building ─────────────────────────────────────────────────


def test_report_empty_collector(collector):
    report = build_latency_report(collector)
    assert report["models"] == {}
    assert report["ranking"] == []


def test_report_per_model_stats(collector):
    for _ in range(10):
        collector.record_llm_latency("model-a", 100)
    for _ in range(10):
        collector.record_llm_latency("model-b", 300)
    report = build_latency_report(collector)
    assert report["models"]["model-a"]["calls"] == 10
    assert report["models"]["model-a"]["median_ms"] == 100.0
    assert report["models"]["model-b"]["median_ms"] == 300.0


def test_ranking_fastest_first(collector):
    for _ in range(5):
        collector.record_llm_latency("slow", 900)
    for _ in range(5):
        collector.record_llm_latency("fast", 100)
    report = build_latency_report(collector)
    assert report["ranking"][0] == "fast"
    assert report["ranking"][1] == "slow"


def test_ranking_excludes_under_sampled(collector):
    collector.record_llm_latency("one-off", 50)  # only 1 call
    for _ in range(MIN_CALLS_FOR_RANKING):
        collector.record_llm_latency("steady", 200)
    report = build_latency_report(collector)
    assert "one-off" not in report["ranking"]
    assert "steady" in report["ranking"]
    # Stats still include the under-sampled model.
    assert "one-off" in report["models"]


def test_p95_reported(collector):
    for i in range(20):
        collector.record_llm_latency("m", float(100 + i))
    report = build_latency_report(collector)
    assert report["models"]["m"]["p95_ms"] > report["models"]["m"]["median_ms"]


# ── formatting ──────────────────────────────────────────────────────


def test_format_empty():
    block = format_latency_report({"models": {}, "ranking": []})
    assert "no latency data" in block


def test_format_has_rows_and_fastest(collector):
    for _ in range(5):
        collector.record_llm_latency("fast-model", 120)
    for _ in range(5):
        collector.record_llm_latency("slow-model", 800)
    block = format_latency_report(build_latency_report(collector))
    assert "fast-model" in block
    assert "slow-model" in block
    assert "fastest" in block
