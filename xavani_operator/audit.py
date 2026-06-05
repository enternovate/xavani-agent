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
import time
from typing import Any

_GENESIS = "GENESIS"


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

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Append ``event``; return the full record (with its chain hash)."""
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
