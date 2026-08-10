# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Mechanical 'shake' pass that runs BEFORE LLM compaction.

Free token reduction: strip repeated tool boilerplate before paying for an
LLM summary. This module is pure and deterministic — it never calls an LLM
and never touches anything outside the message list it is given.

Rules:

1. **Collapse repeated tool outputs.** Consecutive tool messages whose
   content is identical after whitespace normalization collapse into a
   single message with a ``(repeated Nx)`` marker appended. The *last*
   occurrence of the run is the one kept (with its metadata) — the last
   occurrence of any content is never dropped.

2. **Remove decorative banner lines.** Lines made only of ``=``, ``-`` or
   ``*`` characters longer than 20 chars that appear 3+ times across all
   tool results are removed from every tool result. They are decoration,
   not content, so their removal does not lose information.

3. **Only tool-result content is eligible.** User and assistant text
   messages pass through untouched (same object, byte-identical). Tool
   messages whose content is not a plain string (multimodal part lists,
   ``None``) are also untouched.

4. **Never drop the last occurrence of anything.** The last message of the
   input always survives, and each collapsed run keeps its last occurrence.

5. **Purity.** The input list is never mutated; a new list is returned.
   Messages that are not modified are shared by reference.

The shake is idempotent in practice: running it again on its own output
finds no new duplicate runs (collapsed runs are no longer adjacent
identicals) and no remaining qualifying banners.
"""

from typing import Any, Dict, List

# A banner line is made solely of these characters (after stripping).
_BANNER_CHARS = frozenset("=-*")
# "longer than 20 chars" — a line of exactly 20 separator chars is kept.
_BANNER_MIN_LEN = 20
# Minimum appearances before a banner line is removed.
_BANNER_MIN_COUNT = 3


def _normalize_ws(text: str) -> str:
    """Whitespace-normalized view used for exact-match comparison.

    Collapses every run of whitespace to a single space and strips the
    ends, so ``"a\\n\\n  b"`` and ``"a b"`` compare equal.
    """
    return " ".join(text.split())


def _is_banner_line(line: str) -> bool:
    """True if ``line`` is a decorative separator: only =, -, * chars and
    longer than 20 chars (after stripping surrounding whitespace)."""
    stripped = line.strip()
    return len(stripped) > _BANNER_MIN_LEN and all(c in _BANNER_CHARS for c in stripped)


def _count_banners(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count occurrences of each banner line across all eligible tool results.

    The key is the stripped line so leading/trailing whitespace around the
    separator does not defeat the count.
    """
    counts: Dict[str, int] = {}
    for msg in messages:
        # Only tool-result content is eligible for banner removal; banners
        # in user/assistant text must never count toward the threshold.
        if not isinstance(msg, dict) or msg.get("role") != "tool":
            continue
        content = msg.get("content")
        if not isinstance(content, str):
            continue
        for line in content.split("\n"):
            if _is_banner_line(line):
                key = line.strip()
                counts[key] = counts.get(key, 0) + 1
    return counts


def _remove_banners(content: str, banner_counts: Dict[str, int]) -> str:
    """Remove every banner line whose stripped form appears 3+ times."""
    doomed = {
        stripped
        for stripped, count in banner_counts.items()
        if count >= _BANNER_MIN_COUNT
    }
    if not doomed:
        return content
    kept_lines = [
        line
        for line in content.split("\n")
        if not (_is_banner_line(line) and line.strip() in doomed)
    ]
    return "\n".join(kept_lines)


def shake(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Shake a message list down before it is paid for by an LLM summary.

    Returns a new list; the input is never mutated. Only tool messages
    with plain-string content are candidates for modification.
    """
    if not isinstance(messages, list):
        return messages
    if not messages:
        return []

    banner_counts = _count_banners(messages)

    result: List[Dict[str, Any]] = []
    i = 0
    n = len(messages)
    while i < n:
        msg = messages[i]
        content = msg.get("content") if isinstance(msg, dict) else None

        # Collapse a run of consecutive identical tool outputs.
        if (
            isinstance(msg, dict)
            and msg.get("role") == "tool"
            and isinstance(content, str)
        ):
            norm = _normalize_ws(content)
            j = i + 1
            while j < n:
                nxt = messages[j]
                nxt_content = nxt.get("content") if isinstance(nxt, dict) else None
                if not (
                    isinstance(nxt, dict)
                    and nxt.get("role") == "tool"
                    and isinstance(nxt_content, str)
                    and _normalize_ws(nxt_content) == norm
                ):
                    break
                j += 1
            run_len = j - i
            if run_len > 1:
                # Keep the LAST occurrence of the run — never drop it.
                kept = dict(messages[j - 1])
                cleaned = _remove_banners(kept["content"], banner_counts)
                kept["content"] = cleaned.rstrip() + f"\n(repeated {run_len}x)"
                result.append(kept)
                i = j
                continue

        # Not part of a collapse run: still eligible for banner removal.
        if (
            isinstance(msg, dict)
            and msg.get("role") == "tool"
            and isinstance(content, str)
        ):
            cleaned = _remove_banners(content, banner_counts)
            if cleaned != content:
                msg = dict(msg)
                msg["content"] = cleaned

        result.append(msg)
        i += 1

    return result
