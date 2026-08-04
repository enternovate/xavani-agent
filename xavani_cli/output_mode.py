# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C11: --brief / --verbose output modes.

Two explicit output modes for CLI runs:

- brief:   tool progress off, final answer only (CI, automation)
- verbose: tool progress on (all), timing + metadata footers on

The mode is a display-layer preference: it never changes agent behavior,
only how much of the run the user sees.

Usage::

    from xavani_cli.output_mode import resolve_output_mode, apply_output_mode

    mode = resolve_output_mode(brief_flag=False, verbose_flag=False)
    apply_output_mode(mode)   # writes the in-process display config
"""

from __future__ import annotations

import os
from typing import Optional

BRIEF = "brief"
VERBOSE = "verbose"
DEFAULT = "default"

_VALID = {BRIEF, VERBOSE, DEFAULT}


def resolve_output_mode(brief: bool = False, verbose: bool = False) -> str:
    """Resolve the effective output mode from CLI flags and env.

    Explicit flags win. XAVANI_OUTPUT_MODE provides the default when no
    flag is given. Unknown env values fall back to ``default``.
    """
    if brief and verbose:
        return DEFAULT  # contradictory flags — neutral default
    if brief:
        return BRIEF
    if verbose:
        return VERBOSE
    env = os.environ.get("XAVANI_OUTPUT_MODE", "").strip().lower()
    if env in _VALID:
        return env
    return DEFAULT


def apply_output_mode(mode: str) -> dict:
    """Apply the mode to the process (returns the config changes).

    Does NOT touch config.yaml — this is a per-run display override.
    """
    if mode == BRIEF:
        return {
            "tool_progress": "off",
            "show_metadata_footer": False,
            "show_reasoning": False,
        }
    if mode == VERBOSE:
        return {
            "tool_progress": "verbose",
            "show_metadata_footer": True,
            "show_reasoning": True,
        }
    return {
        "tool_progress": "new",
        "show_metadata_footer": False,
        "show_reasoning": False,
    }


def mode_label(mode: str) -> str:
    """Human label for a mode."""
    return {
        BRIEF: "brief (tool progress off, answers only)",
        VERBOSE: "verbose (tool progress on, timing + metadata)",
        DEFAULT: "default",
    }.get(mode, mode)
