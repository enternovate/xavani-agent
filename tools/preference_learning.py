# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C08: per-user preference learning.

Learns durable user preferences from explicit correction patterns
("always use X", "I prefer Y", "stop doing Z") and stores them per
user. Stored preferences feed the context prefetch (G08) so future
sessions start with the user's known preferences.

Deterministic extraction (no LLM): only EXPLICIT preference statements
are learned — the system never guesses preferences from vague text.

Usage::

    from tools.preference_learning import (
        extract_preferences,
        learn_from_message,
        preferences_for,
    )

    facts = extract_preferences("Always use pytest for tests.")
    learn_from_message("user-42", "Always use pytest for tests.")
    prefs = preferences_for("user-42")
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Explicit preference patterns (applied per sentence). Capture the
# statement for context. Ordered: strongest signals first.
_PREFERENCE_PATTERNS = (
    re.compile(
        r"\b(?:always|never|please always)\s+(?:use|do|run|call|prefer)\b"
        r".{0,120}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI (?:prefer|like|want|need|require|insist on)\b"
        r".{0,120}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:stop|don'?t|do not)\s+(?:using|doing|running|calling)\b"
        r".{0,120}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfrom now on\b.{0,120}",
        re.IGNORECASE,
    ),
)

# Split text into sentences so one statement never swallows another.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Statements that look like preferences but are one-off requests.
_ONE_OFF_RE = re.compile(
    r"\b(?:this (?:time|once)|for now|today|right now|in this (?:case|session))\b",
    re.IGNORECASE,
)

_IGNORE_RE = re.compile(
    r"\b(?:please|thanks|thank you|ok|okay|sure|yes|no|got it)\b\s*$",
    re.IGNORECASE,
)

# Vague objects that carry no learnable preference.
_VAGUE_OBJECT_RE = re.compile(r"\b(?:it|this|that|them|those|things?)\s*$", re.IGNORECASE)

_lock = threading.Lock()
_cache: Dict[str, Dict[str, Any]] = {}  # user_id -> {pref_text: {ts, count}}


def _prefs_path(home: Optional[Path] = None) -> Path:
    base = home if home is not None else Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return base / "data" / "user_preferences.json"


def extract_preferences(text: str) -> List[str]:
    """Extract explicit preference statements from text (deterministic).

    Returns normalized preference statements. Empty when the text is a
    one-off request or contains no explicit preference marker.
    """
    if not text:
        return []
    if _ONE_OFF_RE.search(text):
        return []
    statements: List[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        for pattern in _PREFERENCE_PATTERNS:
            match = pattern.search(sentence)
            if not match:
                continue
            statement = re.sub(r"\s+", " ", match.group(0)).strip()
            statement = statement.rstrip(".,!?")
            if len(statement) < 8:
                continue
            if _IGNORE_RE.search(statement):
                continue
            if _VAGUE_OBJECT_RE.search(statement):
                continue
            if statement not in statements:
                statements.append(statement)
    return statements


def _load(home: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    path = _prefs_path(home)
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("preference load failed: %s", exc)
    return {}


def _save(data: Dict[str, Dict[str, Any]], home: Optional[Path] = None) -> None:
    try:
        path = _prefs_path(home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning("preference save failed: %s", exc)


def learn_from_message(user_id: str, text: str, home: Optional[Path] = None) -> List[str]:
    """Learn preferences from a user message. Returns the new statements."""
    statements = extract_preferences(text)
    if not statements:
        return []
    # Normalize for storage: extraction strips trailing punctuation on
    # first pass, but callers may pass pre-normalized text; keep keys
    # consistent so repeated statements dedupe.
    normalized = [s.rstrip(".,!?") for s in statements]
    with _lock:
        data = _load(home)
        user_prefs = data.setdefault(user_id, {})
        learned: List[str] = []
        for statement in normalized:
            entry = user_prefs.get(statement)
            if entry is None:
                user_prefs[statement] = {"ts": time.time(), "count": 1}
                learned.append(statement)
            else:
                entry["count"] = int(entry.get("count", 0)) + 1
        _save(data, home)
    return learned


def preferences_for(user_id: str, home: Optional[Path] = None) -> List[str]:
    """Return the user's learned preferences, most-confirmed first."""
    with _lock:
        data = _load(home)
        user_prefs = data.get(user_id, {})
        ordered = sorted(
            user_prefs.items(),
            key=lambda kv: (int(kv[1].get("count", 0)), kv[1].get("ts", 0)),
            reverse=True,
        )
        return [statement for statement, _meta in ordered]


def all_preferences(home: Optional[Path] = None) -> Dict[str, List[str]]:
    """All users' preferences: {user_id: [statements]}."""
    with _lock:
        data = _load(home)
        return {
            uid: [
                statement
                for statement, _meta in sorted(
                    prefs.items(),
                    key=lambda kv: (int(kv[1].get("count", 0)), kv[1].get("ts", 0)),
                    reverse=True,
                )
            ]
            for uid, prefs in data.items()
        }
