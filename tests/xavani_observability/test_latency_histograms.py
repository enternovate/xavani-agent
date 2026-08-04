# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E01: latency histograms per tool (p50/p95/p99) + Prometheus render."""

from xavani_observability.metrics import MetricsCollector
from xavani_observability.prometheus import render_metrics_text


# ── summary percentiles ─────────────────────────────────────────────


def test_summary_has_p50_p95_p99():
    mc = MetricsCollector(persist_path=None)
    for ms in (10, 20, 30, 40, 100, 200, 300):
        mc.record_tool_latency("read_file", ms)
    summary = mc.get_summary()
    stats = summary["tools"]["read_file"]
    assert stats["call_count"] == 7
    assert stats["p50_ms"] == 40.0
    # Interpolated percentiles: p95 between 200 and 300, p99 >= p95.
    assert stats["p95_ms"] > 200.0
    assert stats["p99_ms"] >= stats["p95_ms"]
    assert stats["p95_ms"] >= stats["p50_ms"]


def test_summary_single_sample_percentiles():
    mc = MetricsCollector(persist_path=None)
    mc.record_tool_latency("write_file", 42.0)
    stats = mc.get_summary()["tools"]["write_file"]
    assert stats["p50_ms"] == stats["p95_ms"] == stats["p99_ms"] == 42.0


def test_empty_summary_no_tools():
    mc = MetricsCollector(persist_path=None)
    assert mc.get_summary()["tools"] == {}


# ── Prometheus text render ──────────────────────────────────────────


def test_render_includes_type_lines():
    mc = MetricsCollector(persist_path=None)
    mc.record_tool_latency("read_file", 10.0)
    text = render_metrics_text(mc.get_summary())
    assert "# TYPE xavani_tool_calls_total counter" in text
    assert "# TYPE xavani_tool_latency_ms summary" in text
    assert "# TYPE xavani_tool_errors_total counter" in text


def test_render_emits_quantiles_per_tool():
    mc = MetricsCollector(persist_path=None)
    for ms in (10, 20, 30):
        mc.record_tool_latency("read_file", ms)
    text = render_metrics_text(mc.get_summary())
    assert 'xavani_tool_latency_ms{tool="read_file",quantile="0.5"}' in text
    assert 'xavani_tool_latency_ms{tool="read_file",quantile="0.95"}' in text
    assert 'xavani_tool_latency_ms{tool="read_file",quantile="0.99"}' in text
    assert 'xavani_tool_calls_total{tool="read_file"} 3' in text


def test_render_escapes_tool_names():
    mc = MetricsCollector(persist_path=None)
    mc.record_tool_latency('weird"tool', 5.0)
    text = render_metrics_text(mc.get_summary())
    assert 'weird\\"tool' in text


def test_render_includes_aggregates():
    mc = MetricsCollector(persist_path=None)
    mc.record_tool_latency("read_file", 5.0)
    mc.record_llm_latency("model-x", 100.0)
    mc.record_tool_error("read_file", "timeout")
    text = render_metrics_text(mc.get_summary())
    assert "xavani_total_tool_calls 1" in text
    assert "xavani_total_llm_calls 1" in text
    assert "xavani_total_errors 1" in text
    assert "xavani_overall_error_rate" in text


def test_render_error_rate_dict():
    mc = MetricsCollector(persist_path=None)
    mc.record_tool_latency("read_file", 5.0)
    mc.record_tool_error("read_file", "timeout")
    text = render_metrics_text(mc.get_summary())
    assert 'xavani_tool_errors_total{tool="read_file"}' in text


def test_render_empty_summary():
    mc = MetricsCollector(persist_path=None)
    text = render_metrics_text(mc.get_summary())
    assert "xavani_total_tool_calls 0" in text
