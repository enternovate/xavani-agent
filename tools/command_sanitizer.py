# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D13: sanitizer for LLM-generated execution input.

Models sometimes wrap code arguments in markdown fences
(`````python ... `````). Executing the raw argument would either crash
on the fence lines or — worse — execute trailing prose after the
closing fence as part of the program.

This module extracts the first fenced block when fences are present and
drops everything after the closing fence. Input without fences passes
through unchanged, so normal tool-call arguments are never altered.

Only used at execution boundaries (execute_code). Not a security
boundary by itself — the sandbox and tirith still do the real defense.
"""

from __future__ import annotations

import re

# Matches ``` or ~~~ fences (3+ backticks/tildes), optionally followed
# by a language tag. The opening fence must be the first non-space
# content on its line.
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)\s*([A-Za-z0-9_+-]*)\s*$")

_CLOSING_FENCE_RE = re.compile(r"^\s*(```+|~~~+)\s*$")


def has_fenced_block(code: str) -> bool:
    """True when the input contains a markdown fenced code block."""
    if not code:
        return False
    for line in code.splitlines():
        if _FENCE_RE.match(line):
            return True
    return False


def sanitize_execution_input(code: str) -> str:
    """Return the executable code from a possibly fence-wrapped argument.

    Rules:
    - No fence -> return the input unchanged.
    - Fence present -> return the first fenced block's content, with the
      opening language tag removed and the closing fence consumed.
    - Anything after the closing fence is dropped (prose or injected
      trailing commands).
    - Never raises; returns the original on any anomaly.
    """
    if not code or not isinstance(code, str):
        return code or ""
    if not has_fenced_block(code):
        return code

    lines = code.splitlines()
    # Find the first opening fence.
    start = None
    fence_char = ""
    for i, line in enumerate(lines):
        m = _FENCE_RE.match(line)
        if m:
            start = i
            fence_char = m.group(1)[0]
            break
    if start is None:
        return code

    # Collect lines until the matching closing fence (same char, 3+).
    body: list[str] = []
    for line in lines[start + 1 :]:
        if _CLOSING_FENCE_RE.match(line) and line.strip()[0] == fence_char:
            break
        body.append(line)

    extracted = "\n".join(body).strip()
    if not extracted:
        # Empty fence body — fall back to the raw input rather than
        # executing nothing (a model may have sent a comment-only block).
        return code
    return extracted


def sanitize_shell_command(command: str) -> str:
    """Strip a single layer of markdown fences from a shell command.

    Unlike execute_code, shell commands arrive as plain strings from the
    model. A fence-wrapped command is almost always a model formatting
    slip; unwrap it so the real command executes. Input without fences
    passes through unchanged.
    """
    return sanitize_execution_input(command)
