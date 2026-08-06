#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""G02: daily learning digest — no_agent cron script.

Summarizes the last day's episodes from xavani_memory and prints a
markdown digest (topics + proposed skill updates).  Empty stdout when
there are no episodes, which the cron engine treats as a silent run.

Usage:
    python3 scripts/daily_learning_digest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    try:
        from xavani_memory.manager import MemoryManager

        with MemoryManager(auto_maintenance=False) as manager:
            print(manager.build_daily_digest(days=1), end="")
    except Exception as exc:
        print(f"daily_learning_digest failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
