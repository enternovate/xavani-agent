# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E02: distributed tracing tests."""

import pytest

import xavani_observability.trace_store as ts
from xavani_observability.trace_store import (
    MAX_EVENTS,
    TraceStore,
    begin_span,
    end_span,
    reset_trace_store,
    trace_store,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_trace_store()
    yield
    reset_trace_store()


# ── store basics ───────────────────────────────────────────────────


def test_emit_assigns_span_id():
    store = TraceStore()
    span_id = store.emit({"cid": "c1", "name": "call", "start_ms": 0})
    assert span_id
    assert store.event_count() == 1


def test_emit_preserves_fields():
    store = TraceStore()
    store.emit({
        "span_id": "s1", "cid": "c1", "name": "tool_call",
        "component": "tools", "kind": "span", "start_ms": 10,
        "tags": {"tool": "read_file"},
    })
    trace = store.get_trace("c1")
    assert trace[0]["name"] == "tool_call"
    assert trace[0]["component"] == "tools"
    assert trace[0]["tags"] == {"tool": "read_file"}


def test_get_trace_filters_by_cid():
    store = TraceStore()
    store.emit({"cid": "a", "name": "x"})
    store.emit({"cid": "b", "name": "y"})
    assert len(store.get_trace("a")) == 1
    assert len(store.get_trace("b")) == 1
    assert len(store.get_trace("ghost")) == 0


def test_ring_buffer_caps_events():
    store = TraceStore(max_events=10)
    for i in range(20):
        store.emit({"cid": f"c{i}", "name": f"n{i}"})
    assert store.event_count() == 10


def test_all_cids():
    store = TraceStore()
    store.emit({"cid": "a", "name": "x"})
    store.emit({"cid": "b", "name": "y"})
    store.emit({"cid": "a", "name": "z"})
    assert set(store.all_cids()) == {"a", "b"}


def test_clear():
    store = TraceStore()
    store.emit({"cid": "a", "name": "x"})
    store.clear()
    assert store.event_count() == 0


# ── span lifecycle ─────────────────────────────────────────────────


def test_begin_end_span_reconstructs():
    store = TraceStore()
    span_id = store.emit({"span_id": "s1", "cid": "c1", "name": "call", "kind": "span", "start_ms": 0, "end_ms": 0})
    store.emit({"span_id": "s1", "cid": "c1", "kind": "end", "end_ms": 250})
    spans = store.get_spans("c1")
    assert len(spans) == 1
    assert spans[0]["span_id"] == span_id
    assert spans[0]["end_ms"] == 250


def test_begin_span_helper():
    span_id = begin_span("tool_call", cid="c1", component="tools", tags={"tool": "x"})
    end_span(span_id, cid="c1")
    store = trace_store()
    spans = store.get_spans("c1")
    assert len(spans) == 1
    assert spans[0]["name"] == "tool_call"
    assert spans[0]["component"] == "tools"
    assert spans[0]["end_ms"] >= spans[0]["start_ms"]


def test_unfinished_span_has_zero_end():
    store = TraceStore()
    store.emit({"span_id": "s1", "cid": "c1", "name": "open", "kind": "span", "start_ms": 5})
    spans = store.get_spans("c1")
    assert spans[0]["end_ms"] == 0.0


# ── singleton ──────────────────────────────────────────────────────


def test_singleton():
    store1 = trace_store()
    store2 = trace_store()
    assert store1 is store2


def test_reset():
    reset_trace_store()
    store = trace_store()
    store.emit({"cid": "a", "name": "x"})
    assert store.event_count() == 1
