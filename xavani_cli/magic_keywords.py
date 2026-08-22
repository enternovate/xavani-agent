# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Magic keywords: lowercase words that opt a turn into special behavior.

Recognised only in prose — never inside fenced code blocks, inline code
spans, XML/HTML tags, or path-like tokens.
"""

import re

_DIRECTIVES = {
    "ultrathink": (
        "[system note: the user asked for careful reasoning — work through "
        "this step by step and double-check the result before answering.]"
    ),
    "orchestrate": (
        "[system note: the user asked for orchestration — split this into "
        "independent subtasks, run them in parallel where possible, and "
        "verify each phase's result before moving on.]"
    ),
    "workflowz": (
        "[system note: the user asked for a deterministic workflow — write "
        "an explicit ordered plan first, then execute each step exactly once "
        "in order.]"
    ),
}

_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_TAG_RE = re.compile(r"<[^>\n]+>")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-./]*")


def _prose_only(text: str) -> str:
    stripped = _FENCED_CODE_RE.sub(" ", text)
    stripped = _INLINE_CODE_RE.sub(" ", stripped)
    stripped = _TAG_RE.sub(" ", stripped)
    return stripped


def detect_magic_keywords(text: str) -> list:
    """Return magic keywords present in prose, in canonical order."""
    prose_words = set(_WORD_RE.findall(_prose_only(text)))
    return [kw for kw in _DIRECTIVES if kw in prose_words]


def apply_magic_keywords(text: str) -> tuple:
    """Return ``(augmented_text, detected_keywords)``.

    Detected keywords are removed from their position and their directive
    notes are appended after the original text so the model sees them as
    turn-level instructions.
    """
    detected = detect_magic_keywords(text)
    if not detected:
        return text, []
    cleaned = _prose_only(text)
    # Rebuild the original text minus standalone keyword tokens.
    for kw in detected:
        cleaned = re.sub(
            rf"(?<![A-Za-z0-9_\-./]){re.escape(kw)}(?![A-Za-z0-9_\-./])",
            "",
            cleaned,
            count=1,
        )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    directives = "\n".join(_DIRECTIVES[kw] for kw in detected)
    return f"{cleaned}\n\n{directives}".strip(), detected
