# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E04: span waterfall tests."""

from xavani_observability.span_waterfall import (
    _span_duration,
    render_waterfall,
    render_waterfall_tree,
)


def _span(span_id, name, start, end, parent_id=None):
    span = {
        "span_id": span_id,
        "name": name,
        "start_ms": start,
        "end_ms": end,
    }
    if parent_id is not None:
        span["parent_id"] = parent_id
    return span


# ── duration ───────────────────────────────────────────────────────


def test_span_duration():
    assert _span_duration(_span("s1", "x", 10, 250)) == 240.0


def test_span_duration_clamped():
    assert _span_duration(_span("s1", "x", 250, 10)) == 0.0


# ── waterfall rendering ────────────────────────────────────────────


def test_empty_spans():
    assert render_waterfall([]) == "(no spans)"


def test_single_span_rendered():
    out = render_waterfall([_span("s1", "tool_call", 0, 250)])
    assert "tool_call" in out
    assert "0.0" in out
    assert "250.0" in out
    assert "#" in out  # the bar


def test_spans_sorted_by_start():
    out = render_waterfall([
        _span("s2", "second", 100, 200),
        _span("s1", "first", 0, 50),
    ])
    assert out.index("first") < out.index("second")


def test_child_indented_under_parent():
    out = render_waterfall_tree([
        _span("s1", "parent", 0, 200),
        _span("s2", "child", 10, 150, parent_id="s1"),
    ])
    assert out.index("parent") < out.index("child")
    assert "  - child" in out  # one indent level


def test_grandchild_indented_twice():
    out = render_waterfall_tree([
        _span("s1", "root", 0, 300),
        _span("s2", "mid", 10, 250, parent_id="s1"),
        _span("s3", "leaf", 20, 100, parent_id="s2"),
    ])
    assert "    - leaf" in out


def test_tree_renders_durations():
    out = render_waterfall_tree([_span("s1", "call", 0, 100)])
    assert "call (100.0 ms)" in out


def test_bar_width_scales_with_duration():
    # Both spans in one waterfall: the bar is relative to the longest.
    out = render_waterfall(
        [
            _span("s1", "fast", 0, 1),
            _span("s2", "slow", 0, 1000),
        ],
        bar_width=40,
    )
    fast_line = [l for l in out.splitlines() if "fast" in l][0]
    slow_line = [l for l in out.splitlines() if "slow" in l][0]
    assert fast_line.count("#") < slow_line.count("#")


def test_unknown_span_id_handled():
    out = render_waterfall([{"name": "orphan", "start_ms": 0, "end_ms": 10}])
    assert "orphan" in out
