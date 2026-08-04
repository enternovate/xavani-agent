# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E04: span waterfall.

Renders a trace's spans as a waterfall: each span is a row with its
duration bar, parent-child nesting, and timing labels. The renderer is
pure — it takes span events and returns text — so it is testable
without any tracing infrastructure.

Span event shape::

    {
        "span_id": "s1",
        "parent_id": None | "s0",
        "name": "tool_call",
        "start_ms": 0.0,
        "end_ms": 250.0,
        "tags": {"tool": "read_file"},
    }

Usage::

    from xavani_observability.span_waterfall import render_waterfall

    print(render_waterfall(spans))
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

BAR_WIDTH = 40


def _span_duration(span: Dict[str, Any]) -> float:
    return max(0.0, float(span.get("end_ms", 0)) - float(span.get("start_ms", 0)))


def _sort_spans(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(spans, key=lambda s: (float(s.get("start_ms", 0)), str(s.get("span_id", ""))))


def render_waterfall(
    spans: List[Dict[str, Any]],
    *,
    bar_width: int = BAR_WIDTH,
) -> str:
    """Render spans as an ASCII waterfall.

    Columns: name | duration bar | start-end ms. Rows are sorted by
    start time; children are indented under their parent.
    """
    if not spans:
        return "(no spans)"

    ordered = _sort_spans(spans)
    total_duration = max(
        (float(s.get("end_ms", 0)) for s in ordered),
        default=0.0,
    )
    total_duration = max(total_duration, 1e-9)
    start_min = min(float(s.get("start_ms", 0)) for s in ordered)

    parents: Dict[str, Optional[str]] = {
        str(s.get("span_id")): s.get("parent_id") for s in ordered
    }
    depth: Dict[str, int] = {}
    for span in ordered:
        span_id = str(span.get("span_id"))
        parent = parents.get(span_id)
        if parent and parent in depth:
            depth[span_id] = depth[parent] + 1
        else:
            depth[span_id] = 0

    lines = ["Span waterfall:"]
    lines.append(f"  {'name':<32} {'bar':<{bar_width}} {'start':>8} {'end':>8} {'dur':>8}")
    for span in ordered:
        span_id = str(span.get("span_id"))
        name = str(span.get("name") or span_id or "?")
        indent = "  " * depth.get(span_id, 0)
        start = float(span.get("start_ms", 0))
        end = float(span.get("end_ms", 0))
        duration = _span_duration(span)
        bar_len = max(1, int((duration / total_duration) * bar_width))
        bar = "#" * min(bar_len, bar_width)
        lines.append(
            f"  {indent + name:<32} {bar:<{bar_width}} "
            f"{start:>8.1f} {end:>8.1f} {duration:>8.1f}"
        )
    return "\n".join(lines)


def render_waterfall_tree(
    spans: List[Dict[str, Any]],
    *,
    bar_width: int = BAR_WIDTH,
) -> str:
    """Render only the tree structure (names + nesting + durations)."""
    if not spans:
        return "(no spans)"
    ordered = _sort_spans(spans)
    parents: Dict[str, Optional[str]] = {
        str(s.get("span_id")): s.get("parent_id") for s in ordered
    }
    depth: Dict[str, int] = {}
    for span in ordered:
        span_id = str(span.get("span_id"))
        parent = parents.get(span_id)
        if parent and parent in depth:
            depth[span_id] = depth[parent] + 1
        else:
            depth[span_id] = 0
    lines = ["Trace tree:"]
    for span in ordered:
        name = str(span.get("name") or span.get("span_id") or "?")
        duration = _span_duration(span)
        lines.append(f"{'  ' * depth.get(str(span.get('span_id')), 0)}- {name} ({duration:.1f} ms)")
    return "\n".join(lines)
