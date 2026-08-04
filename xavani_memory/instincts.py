# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B01: instinct registry — pattern-completion engine.

Persists observed patterns (tool-call chains, failure sequences) with a
count of how often they occurred. When a new session matches a stored
pattern, the registry surfaces the context: "this looks like session X,
where the fix was Y."

Deterministic (no LLM): patterns are exact tool-call chains (2-4 tools
in sequence) extracted from session episodes. Confidence grows with
frequency. Injections are best-effort — the agent always sees them as
advisory context, never as instructions.

Storage: JSON at <XAVANI_HOME>/data/instincts.json
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_PATTERN_COUNT = 2          # a pattern must recur to become an instinct
MAX_PATTERN_CHAIN = 4          # longest tool chain stored
MAX_PATTERNS = 500             # storage bound


def _instincts_path() -> Path:
    home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return home / "data" / "instincts.json"


class InstinctRegistry:
    """Persistent pattern store with frequency-based confidence."""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _instincts_path()
        self._lock = threading.Lock()
        # pattern_key -> {count, last_seen, chains, sessions}
        self._patterns: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ── persistence ──────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._patterns = data.get("patterns", {})
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("instinct registry load failed: %s", exc)
            self._patterns = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"patterns": self._patterns}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("instinct registry save failed: %s", exc)

    # ── recording ────────────────────────────────────────────────────

    def record_episode(self, session_id: str, tool_names: List[str]) -> None:
        """Record the tool-call chain of one episode as pattern evidence.

        Every contiguous 2..MAX_PATTERN_CHAIN sub-sequence of
        ``tool_names`` increments that pattern's count. Repeated
        sessions using the same chain reinforce the instinct.
        """
        names = [n for n in (tool_names or []) if n]
        if len(names) < 2:
            return
        with self._lock:
            for length in range(2, min(len(names), MAX_PATTERN_CHAIN) + 1):
                for i in range(len(names) - length + 1):
                    chain = names[i : i + length]
                    key = "->".join(chain)
                    entry = self._patterns.setdefault(key, {
                        "count": 0,
                        "last_seen": 0.0,
                        "sessions": [],
                        "chain": chain,
                    })
                    entry["count"] += 1
                    entry["last_seen"] = time.time()
                    if session_id and session_id not in entry["sessions"]:
                        entry["sessions"].append(session_id)
            # Enforce the storage bound: drop lowest-count patterns.
            if len(self._patterns) > MAX_PATTERNS:
                self._trim()
        self._save()

    def _trim(self) -> None:
        ordered = sorted(
            self._patterns.items(), key=lambda kv: (kv[1]["count"], kv[1]["last_seen"])
        )
        for key, _ in ordered[: len(ordered) - MAX_PATTERNS]:
            self._patterns.pop(key, None)

    # ── matching ─────────────────────────────────────────────────────

    def match(self, tool_names: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """Find stored patterns matching the given tool sequence.

        A pattern matches when its chain is a contiguous sub-sequence of
        the current tool calls. Returns the strongest matches (highest
        count), each with ``pattern``, ``count``, ``sessions`` and a
        confidence 0..1 (count-based).
        """
        names = [n for n in (tool_names or []) if n]
        if len(names) < 2:
            return []
        hits: List[Dict[str, Any]] = []
        with self._lock:
            for key, entry in self._patterns.items():
                chain = entry.get("chain", [])
                if not chain:
                    continue
                if self._is_subsequence(chain, names):
                    confidence = min(1.0, entry["count"] / 10.0)
                    hits.append({
                        "pattern": key,
                        "count": entry["count"],
                        "sessions": list(entry.get("sessions", []))[:3],
                        "confidence": round(confidence, 2),
                    })
        hits.sort(key=lambda h: (h["count"], h["confidence"]), reverse=True)
        return hits[:limit]

    @staticmethod
    def _is_subsequence(chain: List[str], names: List[str]) -> bool:
        """True when chain appears contiguously inside names."""
        n, m = len(names), len(chain)
        if m > n:
            return False
        for i in range(n - m + 1):
            if names[i : i + m] == chain:
                return True
        return False

    # ── introspection ────────────────────────────────────────────────

    def strongest(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Top patterns by count."""
        with self._lock:
            ordered = sorted(
                self._patterns.items(),
                key=lambda kv: (kv[1]["count"], kv[1]["last_seen"]),
                reverse=True,
            )
        return [
            {
                "pattern": key,
                "count": entry["count"],
                "sessions": len(entry.get("sessions", [])),
            }
            for key, entry in ordered[:limit]
        ]

    def clear(self) -> None:
        """Wipe all patterns. For tests and operator reset."""
        with self._lock:
            self._patterns = {}
        self._save()

    def pattern_count(self) -> int:
        with self._lock:
            return len(self._patterns)


def format_instinct_hint(matches: List[Dict[str, Any]]) -> str:
    """Render instinct matches as advisory context (B01)."""
    if not matches:
        return ""
    lines = ["", "Pattern instincts (advisory — verify before trusting):"]
    for m in matches:
        lines.append(
            f"- tool chain '{m['pattern']}' recurred {m['count']}x "
            f"(confidence {m['confidence']:.0%})"
        )
    lines.append("")
    return "\n".join(lines)
