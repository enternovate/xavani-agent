# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E02: distributed tracing.

A lightweight trace-event store for cross-component correlation.
Components (gateway, agent, tools) emit span events tagged with a
correlation id (C17); this store collects them and reconstructs the
full trace for a correlation id — including spans that crossed process
or component boundaries.

Design: in-memory ring buffer with a hard cap (default 2000 events).
No persistence — traces are for live debugging; persistence invites
stale-data bugs.

Usage::

    from xavani_observability.trace_store import trace_store, begin_span, end_span

    span_id = begin_span("tool_call", cid="abc123", tags={"tool": "read_file"})
    ...
    end_span(span_id, cid="abc123")
    trace = trace_store().get_trace("abc123")
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

MAX_EVENTS = 2000


class TraceStore:
    """Ring-buffer trace event store (thread-safe)."""

    def __init__(self, max_events: int = MAX_EVENTS):
        self._max_events = max_events
        self._lock = threading.Lock()
        self._events: List[Dict[str, Any]] = []

    def emit(self, event: Dict[str, Any]) -> str:
        """Store one span event. Returns its span_id."""
        span_id = str(event.get("span_id") or uuid.uuid4().hex[:12])
        raw_end = event.get("end_ms")
        end_ms = float(raw_end) if raw_end is not None else 0.0
        record = {
            "span_id": span_id,
            "cid": str(event.get("cid") or ""),
            "name": str(event.get("name") or "span"),
            "component": str(event.get("component") or "unknown"),
            "kind": str(event.get("kind") or "span"),  # span | end
            "start_ms": float(event.get("start_ms") or 0.0),
            "end_ms": end_ms,
            "tags": dict(event.get("tags") or {}),
            "ts": time.time(),
        }
        if record["end_ms"] is None:
            record["end_ms"] = record["start_ms"]
        with self._lock:
            self._events.append(record)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
        return span_id

    def get_trace(self, cid: str) -> List[Dict[str, Any]]:
        """All events for a correlation id, in emit order."""
        with self._lock:
            return [dict(e) for e in self._events if e["cid"] == cid]

    def get_spans(self, cid: str) -> List[Dict[str, Any]]:
        """Completed spans (kind=end) for a correlation id."""
        events = self.get_trace(cid)
        spans: Dict[str, Dict[str, Any]] = {}
        for event in events:
            span_id = event["span_id"]
            if event["kind"] == "span":
                spans.setdefault(
                    span_id,
                    {
                        "span_id": span_id,
                        "name": event["name"],
                        "component": event["component"],
                        "start_ms": event["start_ms"],
                        "end_ms": event["end_ms"],
                        "tags": event["tags"],
                    },
                )
            elif event["kind"] == "end":
                if span_id in spans:
                    spans[span_id]["end_ms"] = event["end_ms"]
        return list(spans.values())

    def all_cids(self) -> List[str]:
        with self._lock:
            seen: List[str] = []
            for event in self._events:
                cid = event["cid"]
                if cid and cid not in seen:
                    seen.append(cid)
            return seen

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)


_store: Optional[TraceStore] = None
_store_lock = threading.Lock()


def trace_store() -> TraceStore:
    """Return the process-wide trace store."""
    global _store
    with _store_lock:
        if _store is None:
            _store = TraceStore()
        return _store


def begin_span(name: str, cid: str, component: str = "unknown", tags: Optional[Dict[str, Any]] = None) -> str:
    """Open a span. Returns the span id to pass to end_span."""
    span_id = uuid.uuid4().hex[:12]
    trace_store().emit(
        {
            "span_id": span_id,
            "cid": cid,
            "name": name,
            "component": component,
            "kind": "span",
            "start_ms": time.time() * 1000,
            "tags": tags or {},
        }
    )
    return span_id


def end_span(span_id: str, cid: str) -> None:
    """Close a span opened with begin_span."""
    trace_store().emit(
        {
            "span_id": span_id,
            "cid": cid,
            "name": "end",
            "component": "unknown",
            "kind": "end",
            "end_ms": time.time() * 1000,
        }
    )


def reset_trace_store() -> None:
    """Reset the process-wide store. For tests."""
    global _store
    with _store_lock:
        _store = None
