# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Hash-chained, tamper-evident audit log (v0.7.0 operator U31).

Every consequential operator event — a proposal enqueued, approved, rejected, a
tier-gated action taken — is appended here as a record whose hash chains to the
previous one. Any later edit to a past record breaks the chain, so
:meth:`AuditLog.verify` can detect tampering. This is the accountability spine
behind an autonomous agent: you can always reconstruct *what it did and when*, and
prove the record wasn't altered.

Pure local I/O over the operator state store — **no LLM, no network** (R10).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

_GENESIS = "GENESIS"

# Audit write verbosity (A10). One key controls audit write volume:
#   0 = off (no audit writes)
#   1 = only approval/deny decisions
#   2 = every tool call / request (default — preserves full audit)
# Operators of high-throughput gateways can set XAVANI_AUDIT_LOG=1 to
# cut disk fill while keeping every security decision on record.
_AUDIT_VERBOSITY_DEFAULT = 2
_AUDIT_VERBOSITY_MIN = 0
_AUDIT_VERBOSITY_MAX = 2


def audit_verbosity() -> int:
    """Resolve the configured audit verbosity from XAVANI_AUDIT_LOG."""
    raw = os.environ.get("XAVANI_AUDIT_LOG", str(_AUDIT_VERBOSITY_DEFAULT))
    try:
        level = int(raw)
    except (TypeError, ValueError):
        return _AUDIT_VERBOSITY_DEFAULT
    return max(_AUDIT_VERBOSITY_MIN, min(_AUDIT_VERBOSITY_MAX, level))


def audit_enabled(min_level: int) -> bool:
    """True when the configured verbosity permits a write at min_level."""
    return audit_verbosity() >= min_level


def _hash(payload: dict[str, Any]) -> str:
    """SHA-256 over a canonical JSON encoding of ``payload``."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


class AuditLog:
    """An append-only, hash-chained log persisted in the operator state store."""

    def __init__(self, state, collection: str = "audit") -> None:
        self.state = state
        self.collection = collection

    def append(self, event: dict[str, Any], min_level: int = 1) -> dict[str, Any] | None:
        """Append ``event``; return the full record (with its chain hash).

        ``min_level`` is the verbosity required for this event class:
        decisions default to 1, verbose per-call records pass 2. When the
        configured XAVANI_AUDIT_LOG is below ``min_level`` the event is
        dropped and None is returned.
        """
        if not audit_enabled(min_level):
            return None
        entries = self.state.list(self.collection)
        seq = len(entries)
        prev = entries[-1]["hash"] if entries else _GENESIS
        record = {"seq": seq, "ts": time.time(), "event": event, "prev": prev}
        record["hash"] = _hash(record)
        self.state.put(self.collection, f"{seq:08d}", record)
        return record

    def verify(self) -> bool:
        """True if the whole chain is intact (no record altered or reordered)."""
        prev = _GENESIS
        for entry in self.state.list(self.collection):
            core = {k: entry[k] for k in ("seq", "ts", "event", "prev")}
            if entry["prev"] != prev or entry["hash"] != _hash(core):
                return False
            prev = entry["hash"]
        return True

    def entries(self) -> list[dict[str, Any]]:
        """All records in chain order."""
        return self.state.list(self.collection)
