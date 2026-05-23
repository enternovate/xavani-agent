# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Default SOUL.md template seeded into XAVANI_HOME on first run.

The template is the **base** identity for the agent. On top of it we
splice the mandatory research-guideline pack (loaded by
:mod:`xavani_cli.research_guidelines`) so the principle headers ride
along with every persisted SOUL.md without requiring users to re-edit
their seeds when the pack version bumps.

The composition is deliberately lazy: ``DEFAULT_SOUL_MD`` is computed at
import time, but the underlying loader catches its own errors and
falls back to an empty block, so a malformed guideline never blocks
agent startup.
"""

from __future__ import annotations

_BASE_SOUL_MD = (
    "You are Xavani Agent, an intelligent AI assistant created by Enternovate. "
    "You are helpful, knowledgeable, and direct. You assist users with a wide "
    "range of tasks including answering questions, writing and editing code, "
    "analyzing information, creative work, and executing actions via your tools. "
    "You communicate clearly, admit uncertainty when appropriate, and prioritize "
    "being genuinely useful over being verbose unless otherwise directed below. "
    "Be targeted and efficient in your exploration and investigations."
)


def _build_default_soul() -> str:
    """Compose the base soul with the mandatory research-guideline block."""
    try:
        from xavani_cli.research_guidelines import compose_system_prompt_block

        block = compose_system_prompt_block()
    except Exception:  # pragma: no cover — never block startup
        block = ""

    if not block:
        return _BASE_SOUL_MD

    return _BASE_SOUL_MD + "\n\n" + block.rstrip() + "\n"


DEFAULT_SOUL_MD: str = _build_default_soul()
