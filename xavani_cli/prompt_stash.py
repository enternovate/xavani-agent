# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C08 — Prompt stash: save/restore draft prompts across sessions.

Drafts live as small text files under ``~/.xavani/prompt-stash/`` so they
survive restarts and are easy to back up. Pure stdlib, zero-LLM.

Commands (via ``/stash``):
    /stash <name> <prompt>   save a draft
    /stash list              list saved drafts
    /stash show <name>       print a draft
    /stash load <name>       load a draft into the input queue
    /stash rm <name>         delete a draft
"""

from __future__ import annotations

import re
from pathlib import Path

STASH_DIR_NAME = "prompt-stash"

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def stash_dir(home: Path | None = None) -> Path:
    """Return the stash directory, creating it if needed."""
    base = home or Path.home()
    d = base / ".xavani" / STASH_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _validate_name(name: str) -> str:
    name = (name or "").strip()
    if not _SAFE_NAME.match(name):
        raise ValueError(
            "stash names may contain only letters, digits, dots, dashes and "
            "underscores (1-64 chars)"
        )
    return name


def stash_save(name: str, text: str, home: Path | None = None) -> Path:
    """Save a draft prompt under ``name``. Returns the written path."""
    name = _validate_name(name)
    text = (text or "").strip()
    if not text:
        raise ValueError("cannot stash an empty prompt")
    p = stash_dir(home) / f"{name}.txt"
    p.write_text(text, encoding="utf-8")
    return p


def stash_list(home: Path | None = None) -> list[str]:
    """Return sorted stash names (without the .txt suffix)."""
    d = stash_dir(home)
    return sorted(p.stem for p in d.glob("*.txt") if p.is_file())


def stash_show(name: str, home: Path | None = None) -> str:
    """Return the text of a stashed draft, or raise KeyError."""
    name = _validate_name(name)
    p = stash_dir(home) / f"{name}.txt"
    if not p.is_file():
        raise KeyError(name)
    return p.read_text(encoding="utf-8")


def stash_delete(name: str, home: Path | None = None) -> bool:
    """Delete a stashed draft. Returns True if a file was removed."""
    name = _validate_name(name)
    p = stash_dir(home) / f"{name}.txt"
    if p.is_file():
        p.unlink()
        return True
    return False
