# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S3-6 (E106): ``xavani memory`` command-line interface.

Subcommands:
- view      list stored memory entries
- stats     counts per store
- diagnose  store health (files exist, parseable)
- clear     empty the store (requires --yes)
- enqueue   add an entry
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from xavani_memory.manager import MEMORY_DIR, MemoryManager


def _build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--memory-dir",
        type=Path,
        default=MEMORY_DIR,
        help="Memory directory (default: $XAVANI_HOME/data/memory)",
    )
    parser = argparse.ArgumentParser(
        prog="xavani memory",
        parents=[parent],
        description="Inspect and manage the on-disk Xavani memory stores.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_view = sub.add_parser("view", parents=[parent], help="list stored memory entries")
    p_view.add_argument("--limit", type=int, default=100)

    sub.add_parser("stats", parents=[parent], help="show counts per store")
    sub.add_parser("diagnose", parents=[parent], help="check store health")

    p_clear = sub.add_parser("clear", parents=[parent], help="empty the memory store")
    p_clear.add_argument(
        "--yes", action="store_true", help="confirm the destructive clear"
    )

    p_enqueue = sub.add_parser("enqueue", parents=[parent], help="add a memory entry")
    p_enqueue.add_argument("text", help="the entry text to store")

    return parser


def _cmd_view(manager: MemoryManager, args: argparse.Namespace) -> int:
    entries = manager.episodic.get_recent(limit=args.limit)
    if not entries:
        print("No memory entries.")
        return 0
    for ep in entries:
        ts = (ep.get("timestamp") or "")[:19]
        text = (ep.get("user_input") or "").replace("\n", " ")[:120]
        print(f"[{ep.get('episode_id', '?')}] {ts} {text}")
    print(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")
    return 0


def _cmd_stats(manager: MemoryManager, args: argparse.Namespace) -> int:
    stats = manager.stats()
    ep = stats["episodic"]
    proc = stats["procedural"]
    print(
        f"episodic: {ep['total']} episodes "
        f"({ep['active']} active, {ep['archived']} archived)"
    )
    print(
        f"procedural: {proc['total_outcomes']} outcomes, "
        f"{proc['unique_task_types']} task types, "
        f"{proc['compiled_patterns']} patterns"
    )
    return 0


def _cmd_diagnose(manager: MemoryManager, args: argparse.Namespace) -> int:
    healthy = True
    for store in (manager.episodic, manager.procedural):
        path = store._db_path
        if not path.exists():
            print(f"{path.name}: MISSING ({path})")
            healthy = False
            continue
        try:
            conn = sqlite3.connect(str(path))
            conn.execute("SELECT 1")
            conn.close()
            print(f"{path.name}: OK ({path.stat().st_size} bytes)")
        except sqlite3.Error as exc:
            print(f"{path.name}: UNREADABLE ({exc})")
            healthy = False
    return 0 if healthy else 1


def _cmd_clear(manager: MemoryManager, args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing to clear memory without confirmation. Pass --yes to proceed.")
        return 1
    cleared = manager.clear_all()
    print(
        f"Cleared: {cleared['episodes_cleared']} episodes, "
        f"{cleared['procedural_records_cleared']} procedural records."
    )
    return 0


def _cmd_enqueue(manager: MemoryManager, args: argparse.Namespace) -> int:
    episode_id = manager.remember(
        user_input=args.text, agent_response="", outcome="enqueued"
    )
    print(f"Enqueued {episode_id}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the ``xavani-memory`` console script."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    manager = MemoryManager(memory_dir=args.memory_dir, auto_maintenance=False)
    try:
        handlers = {
            "view": _cmd_view,
            "stats": _cmd_stats,
            "diagnose": _cmd_diagnose,
            "clear": _cmd_clear,
            "enqueue": _cmd_enqueue,
        }
        return handlers[args.command](manager, args)
    finally:
        try:
            manager.stop_maintenance()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
