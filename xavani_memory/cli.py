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
    # Subparser copies use default=SUPPRESS so the flag works on EITHER side
    # of the subcommand: provided after -> sets the value; omitted -> leaves
    # the main parser's value intact (classic argparse shadowing fix).
    sub_parent = argparse.ArgumentParser(add_help=False)
    sub_parent.add_argument(
        "--memory-dir", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS
    )
    parser = argparse.ArgumentParser(
        prog="xavani memory",
        parents=[parent],
        description="Inspect and manage the on-disk Xavani memory stores.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_view = sub.add_parser("view", parents=[sub_parent], help="list stored memory entries")
    p_view.add_argument("--limit", type=int, default=100)

    sub.add_parser("stats", parents=[sub_parent], help="show counts per store")
    sub.add_parser("diagnose", parents=[sub_parent], help="check store health")

    p_clear = sub.add_parser("clear", parents=[sub_parent], help="empty the memory store")
    p_clear.add_argument(
        "--yes", action="store_true", help="confirm the destructive clear"
    )

    p_enqueue = sub.add_parser("enqueue", parents=[sub_parent], help="add a memory entry")
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


def _make_manager(memory_dir: Path) -> MemoryManager:
    """Build the manager, surfacing corrupt-store failures to the caller."""
    return MemoryManager(memory_dir=memory_dir, auto_maintenance=False)


def _cmd_diagnose_direct(memory_dir: Path) -> int:
    """Health-check the store FILES without constructing a manager first.

    A corrupt store can make MemoryManager construction itself raise
    (StateCorruptionError); diagnose exists precisely to report that case
    gracefully instead of tracebacking.
    """
    healthy = True
    # Same filenames MemoryManager uses (manager.py: episodic.db / procedural.db).
    for name in ("episodic.db", "procedural.db"):
        path = memory_dir / name
        if not path.exists():
            print(f"{name}: MISSING ({path})")
            healthy = False
            continue
        try:
            conn = sqlite3.connect(str(path))
            conn.execute("SELECT 1")
            conn.close()
            print(f"{name}: OK ({path.stat().st_size} bytes)")
        except sqlite3.Error as exc:
            print(f"{name}: UNREADABLE ({exc})")
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

    # diagnose must NOT construct the manager first: a corrupt store can
    # make MemoryManager raise, and reporting that gracefully is the whole
    # point of the subcommand (S3-6 review finding).
    if args.command == "diagnose":
        return _cmd_diagnose_direct(args.memory_dir)

    try:
        manager = _make_manager(args.memory_dir)
    except Exception as exc:
        print(f"memory store failed to open: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("Run 'xavani memory diagnose' for a file-level health check.", file=sys.stderr)
        return 1
    try:
        handlers = {
            "view": _cmd_view,
            "stats": _cmd_stats,
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
