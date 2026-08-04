# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C17: gateway request tracing with correlation IDs.

Every incoming message gets a task-local correlation ID that lands in
every log record (gateway -> agent -> tools -> providers).
"""

import contextvars
import logging
import threading

import pytest

from gateway.tracing import (
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


# ── ID generation ────────────────────────────────────────────────────


def test_new_correlation_id_is_short_and_unique():
    a = new_correlation_id()
    b = new_correlation_id()
    assert a != b
    assert len(a) == 12


# ── ContextVar binding ───────────────────────────────────────────────


def test_default_is_empty():
    assert get_correlation_id() == ""


def test_set_and_reset():
    token = set_correlation_id("abc123")
    try:
        assert get_correlation_id() == "abc123"
    finally:
        reset_correlation_id(token)
    assert get_correlation_id() == ""


def test_task_local_isolation():
    """Concurrent tasks must not see each other's cid."""
    import asyncio

    seen = {}

    async def _task(cid):
        token = set_correlation_id(cid)
        try:
            await asyncio.sleep(0.01)
            seen[cid] = get_correlation_id()
        finally:
            reset_correlation_id(token)

    async def _main():
        await asyncio.gather(_task("cid-a"), _task("cid-b"))

    asyncio.run(_main())
    assert seen == {"cid-a": "cid-a", "cid-b": "cid-b"}


# ── Log record injection ─────────────────────────────────────────────


def _make_record():
    """Emit a real log record through the installed factory chain."""
    captured: list = []

    class _Capture(logging.Handler):
        def emit(self, record):
            captured.append(record)

    logger = logging.getLogger("test.cid")
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    handler = _Capture()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        logger.info("hello world")
    finally:
        logger.removeHandler(handler)
    assert captured, "no record captured"
    return captured[0]


def test_record_factory_injects_cid_tag():
    from xavani_logging import _install_session_record_factory

    _install_session_record_factory()
    token = set_correlation_id("trace-me")
    try:
        record = _make_record()
        assert "trace-me" in record.cid_tag  # type: ignore[attr-defined]
    finally:
        reset_correlation_id(token)


def test_record_factory_empty_cid_outside_trace():
    from xavani_logging import _install_session_record_factory

    _install_session_record_factory()
    record = _make_record()
    assert record.cid_tag == ""  # type: ignore[attr-defined]


def test_log_format_includes_cid():
    from xavani_logging import _LOG_FORMAT

    assert "%(cid_tag)s" in _LOG_FORMAT


# ── propagation contract (mirrors A03 harness) ──────────────────────


def test_cid_propagates_via_copy_context():
    """Executor threads (copy_context) must see the parent's cid."""
    token = set_correlation_id("exec-cid")
    try:
        seen: list = []

        def _worker():
            seen.append(get_correlation_id())

        ctx = contextvars.copy_context()
        t = threading.Thread(target=lambda: ctx.run(_worker))
        t.start()
        t.join()
        assert seen == ["exec-cid"]
    finally:
        reset_correlation_id(token)


# ── gateway integration ─────────────────────────────────────────────


def test_handle_message_binds_and_clears_cid(monkeypatch):
    """_handle_message_traced sets a cid for the pipeline and clears it."""
    import asyncio

    from gateway.run import GatewayRunner

    captured = {}

    async def fake_pipeline(self, event):
        captured["active"] = get_correlation_id()
        return "ok"

    monkeypatch.setattr(GatewayRunner, "_handle_message", fake_pipeline)
    # Avoid touching __init__: create an uninitialized instance.
    gw = object.__new__(GatewayRunner)

    result = asyncio.run(GatewayRunner._handle_message_traced(gw, None))  # type: ignore[arg-type]
    assert result == "ok"
    # The pipeline saw a 12-char cid...
    assert len(captured["active"]) == 12
    # ...and it was cleared after the message finished.
    assert get_correlation_id() == ""


def test_adapters_route_through_traced_entry():
    """set_message_handler must receive the cid-binding entry."""
    import inspect

    from gateway.run import GatewayRunner

    assert GatewayRunner._handle_message_traced is not None
    # The adapter registration sites (start + reconnect) reference the
    # traced entry; the plain handler stays intact for command tests.
    src = inspect.getsource(GatewayRunner)
    assert src.count("adapter.set_message_handler(self._handle_message_traced)") >= 2
    assert "_handle_message_traced" in inspect.getsource(GatewayRunner._handle_message_traced)
