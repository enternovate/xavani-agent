# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C17: gateway request tracing with correlation IDs.

Every incoming gateway message gets a correlation ID (``cid``). The ID
lives in a ContextVar, so it propagates task-locally through
gateway -> agent -> tools -> providers without cross-session bleed
(mirrors gateway/session_context.py). A logging record factory injects
the cid into every LogRecord, so log lines across the whole pipeline
carry the same trace tag — no per-call-site logging changes needed.

Example:
    [2026-08-04 10:00:00] [telegram] INFO [cid:c8f3a1] ...
"""

from __future__ import annotations

import contextvars
import uuid
from typing import Optional

# Task-local correlation ID. Empty string = not tracing.
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "gateway_correlation_id",
    default="",
)


def new_correlation_id() -> str:
    """Generate a short, sortable correlation ID."""
    return uuid.uuid4().hex[:12]


def set_correlation_id(cid: str) -> contextvars.Token[str]:
    """Bind a correlation ID to the current context. Returns a token."""
    return _correlation_id.set(cid or "")


def reset_correlation_id(token: contextvars.Token[str]) -> None:
    """Restore the prior correlation ID context."""
    _correlation_id.reset(token)


def get_correlation_id() -> str:
    """Return the active correlation ID, or \"\" when not tracing."""
    return _correlation_id.get()


def install_correlation_record_factory() -> None:
    """Extend the LogRecord factory so every record carries ``cid``.

    Composes with the session_tag injector already installed by
    xavani_logging. Idempotent. Reads the ContextVar at record
    creation time — records outside a traced task get an empty tag.
    """
    import logging

    current_factory = logging.getLogRecordFactory()
    if getattr(current_factory, "_xavani_cid_injector", False):
        return  # already installed

    def _cid_record_factory(*args, **kwargs):
        record = current_factory(*args, **kwargs)
        cid = get_correlation_id()
        record.cid_tag = f" [cid:{cid}]" if cid else ""  # type: ignore[attr-defined]
        return record

    _cid_record_factory._xavani_cid_injector = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(_cid_record_factory)


# Install immediately on import — cid_tag is available on all records
# from this point forward, even before the gateway binds a cid.
install_correlation_record_factory()
