# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""User preference + reference capture (v0.7.0 operator L7).

"Learn everything about the user" — the explicit, durable half. Whenever the user
states a preference ("I like planning first", "prefers dark themes") or references
a design they like, it's recorded here and recalled into generation context so the
agent **defaults to it without being re-told**. Complements
``xavani_learner/user_profile.py`` (which learns communication style passively).

Storage is an injected state object (duck-typed ``put``/``get``/``list`` — the
operator's :class:`OperatorState`); no LLM, no network (R10).
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

_COLLECTION = "preferences"


class PreferenceStore:
    """Persistent store of stated preferences and liked references."""

    def __init__(self, state: Any) -> None:
        self.state = state

    def record(self, text: str, kind: str = "preference") -> str:
        """Record a preference (or reference); return its id. Idempotent per text+kind."""
        pid = hashlib.sha1(f"{kind}:{text}".encode("utf-8")).hexdigest()[:12]
        self.state.put(_COLLECTION, pid, {"text": text, "kind": kind, "ts": time.time()})
        return pid

    def record_reference(self, url: str) -> str:
        """Record a design reference the user likes."""
        return self.record(url, kind="design_reference")

    def list(self, kind: str | None = None) -> list[dict]:
        """All preference records (optionally filtered by kind), oldest first."""
        items = self.state.list(_COLLECTION)
        if kind is not None:
            items = [i for i in items if i.get("kind") == kind]
        return sorted(items, key=lambda i: i.get("ts", 0))

    def recall(self, kind: str | None = None) -> list[str]:
        """The preference texts, for injection into generation context."""
        return [i["text"] for i in self.list(kind)]
