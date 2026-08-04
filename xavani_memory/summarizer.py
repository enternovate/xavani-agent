# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B02: session summarizer with confidence scoring.

At session end, extract durable facts from the session's episodes.
Each fact is stored as (fact, confidence, source). On the next session,
only facts with confidence above a threshold are injected into the
agent's context — all-or-nothing memory injection is replaced with
confidence-filtered recall.

Extraction is deterministic (no LLM): facts come from explicit user
preference statements and from repeated topic mentions across episodes.
Confidence reflects statement strength and corroboration frequency:

- 0.9 — explicit first-person preference ("I use X")
- 0.75 — repeated topic mention (3+ episodes)
- 0.6 — single strong statement ("I don't like X")
- 0.4 — single mention (below the default recall threshold)

Storage: JSONL at <XAVANI_HOME>/data/session_summaries.jsonl, one line
per fact with the session it came from.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE = 0.6
_SUMMARY_DIR = "data"
_SUMMARY_FILE = "session_summaries.jsonl"

# "I use/prefer/want/like X" — strongest signal. Negative phrases are
# handled by _NEGATIVE_RE only (a negative statement is weaker evidence).
_PREFERENCE_RE = re.compile(
    r"\bI (?:use|prefer|want|like|love|need|hate)\b"
    r".{0,80}?\b([A-Za-z][A-Za-z0-9_ .#/-]{2,40})\b",
    re.IGNORECASE,
)
# "I don't like X" — strong negative.
_NEGATIVE_RE = re.compile(
    r"\bI don'?t (?:like|want|use|need)\b.{0,80}?\b([A-Za-z][A-Za-z0-9_ .#/-]{2,40})\b",
    re.IGNORECASE,
)
# Topic tokens for repetition counting: capitalized words, code-like
# tokens (with a dash/dot), and lowercase words of 6+ chars minus
# stopwords. Short lowercase words ("the", "and") are noise.
_TOPIC_TOKEN_RE = re.compile(
    r"\b([A-Z][a-z0-9_]{2,}|[a-z0-9_]+[-.][a-z0-9_]+|[a-z]{6,})\b"
)
_STOPWORDS = frozenset({
    "because", "before", "really", "should", "would", "could",
    "during", "after", "about", "there", "their", "these", "those",
    "something", "nothing", "however", "although", "through",
})


def _summary_path() -> Path:
    home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return home / _SUMMARY_DIR / _SUMMARY_FILE


def extract_facts(episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract (fact, confidence, source) triples from episode dicts.

    Each episode dict must have ``user_input`` (str). Returns a list of
    ``{"fact", "confidence", "source", "session_id"}`` dicts, deduped by
    fact text (highest confidence wins).
    """
    facts: Dict[str, Dict[str, Any]] = {}
    topics: Counter = Counter()

    for episode in episodes:
        text = episode.get("user_input") or ""
        session_id = episode.get("session_id")
        if not text:
            continue
        for token in _TOPIC_TOKEN_RE.findall(text):
            if token.lower() in _STOPWORDS:
                continue
            topics[token] += 1
        for m in _NEGATIVE_RE.finditer(text):
            fact = m.group(0)[:200]
            facts.setdefault(fact, {
                "fact": fact,
                "confidence": 0.6,
                "source": "negative_statement",
                "session_id": session_id,
            })
        for m in _PREFERENCE_RE.finditer(text):
            fact = m.group(0)[:200]
            current = facts.get(fact)
            if current is None or current["confidence"] < 0.9:
                facts[fact] = {
                    "fact": fact,
                    "confidence": 0.9,
                    "source": "preference_statement",
                    "session_id": session_id,
                }

    # Repeated topic mentions (3+ episodes) become corroborated facts.
    for token, count in topics.items():
        if count >= 3 and token not in {f["fact"] for f in facts.values()}:
            facts[token] = {
                "fact": token,
                "confidence": min(0.75, 0.4 + 0.1 * count),
                "source": f"repeated_mention_x{count}",
                "session_id": None,
            }

    return sorted(facts.values(), key=lambda f: f["confidence"], reverse=True)


def store_facts(facts: List[Dict[str, Any]]) -> bool:
    """Append facts to the summary store. Best-effort."""
    try:
        path = _summary_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for fact in facts:
                record = dict(fact)
                record["ts"] = time.time()
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError as exc:
        logger.warning("session summary write failed: %s", exc)
        return False


def recall_facts(
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    limit: int = 20,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return facts above the confidence threshold, newest first.

    When ``session_id`` is given, facts from that session are excluded
    (the current session's own facts are not injected back into itself).
    """
    path = _summary_path()
    facts: List[Dict[str, Any]] = []
    try:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("confidence", 0) < min_confidence:
                    continue
                if session_id and record.get("session_id") == session_id:
                    continue
                facts.append(record)
    except OSError as exc:
        logger.warning("session summary read failed: %s", exc)
        return []
    return list(reversed(facts))[:limit]


def format_recall_prompt(facts: List[Dict[str, Any]]) -> str:
    """Format recalled facts as a compact context injection block."""
    if not facts:
        return ""
    lines = ["", "Recalled durable facts from past sessions (confidence-filtered):"]
    for fact in facts:
        conf = fact.get("confidence", 0)
        lines.append(f"- [{conf:.0%}] {fact.get('fact', '')}")
    lines.append("")
    return "\n".join(lines)
