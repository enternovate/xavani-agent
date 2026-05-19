# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Resolve XAVANI_HOME for standalone skill scripts.

Skill scripts may run outside the Xavani process (e.g. system Python,
nix env, CI) where ``xavani_constants`` is not importable.  This module
provides the same ``get_xavani_home()`` and ``display_xavani_home()``
contracts as ``xavani_constants`` without requiring it on ``sys.path``.

When ``xavani_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``xavani_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``XAVANI_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from xavani_constants import display_xavani_home as display_xavani_home
    from xavani_constants import get_xavani_home as get_xavani_home
except (ModuleNotFoundError, ImportError):

    def get_xavani_home() -> Path:
        """Return the Xavani home directory (default: ~/.xavani).

        Mirrors ``xavani_constants.get_xavani_home()``."""
        val = os.environ.get("XAVANI_HOME", "").strip()
        return Path(val) if val else Path.home() / ".xavani"

    def display_xavani_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``xavani_constants.display_xavani_home()``."""
        home = get_xavani_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
