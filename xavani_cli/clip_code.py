# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Clipboard text helpers: copy the last code block from a reply.

Cross-platform: pbcopy (macOS), clip.exe / powershell Set-Clipboard
(Windows), xclip/xcopy/wl-copy (Linux). The copier is injectable so
tests never touch a real clipboard.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Callable, Optional

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INDENTED_RE = re.compile(r"(?:^|\n)((?: {4,}|\t+)[^\n]+(?:\n(?: {4,}|\t+)[^\n]+)+)")


def last_code_block(text: str) -> Optional[str]:
    """Extract the last fenced block, else the last indented block."""
    if not text:
        return None
    fences = _FENCE_RE.findall(text)
    if fences:
        return fences[-1].strip("\n")
    indented = _INDENTED_RE.findall(text)
    if indented:
        return _dedent(indented[-1])
    return None


def _dedent(block: str) -> str:
    import textwrap

    return textwrap.dedent(block)


def copy_text(
    text: str,
    *,
    copier: Optional[Callable[[str], bool]] = None,
) -> bool:
    """Copy text to the system clipboard; True on success."""
    if not text or not text.strip():
        return False
    if copier is not None:
        return bool(copier(text))
    import platform

    system = platform.system()
    try:
        if system == "Darwin":
            if shutil.which("pbcopy"):
                subprocess.run(
                    ["pbcopy"], input=text.encode("utf-8"), check=True,
                    timeout=10,
                )
                return True
            return False
        if system == "Windows":
            for argv in (["clip"], ["powershell", "-command", "$input | Set-Clipboard"]):
                exe = shutil.which(argv[0])
                if not exe:
                    continue
                subprocess.run(
                    [exe, *argv[1:]], input=text.encode("utf-8"),
                    check=True, timeout=15,
                )
                return True
            return False
        for argv in (
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
            ["wl-copy"],
        ):
            if shutil.which(argv[0]):
                subprocess.run(
                    argv, input=text.encode("utf-8"), check=True, timeout=10,
                )
                return True
        return False
    except (subprocess.SubprocessError, OSError):
        return False


def copy_last_code_block(
    text: str,
    *,
    copier: Optional[Callable[[str], bool]] = None,
) -> tuple[bool, str]:
    """Find and copy the last code block; returns (copied, block-or-reason)."""
    block = last_code_block(text)
    if block is None:
        return False, "no code block found"
    if copy_text(block, copier=copier):
        return True, block
    return False, "no clipboard tool available"
