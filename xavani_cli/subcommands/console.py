"""``xavani console`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_console_parser(subparsers, *, cmd_console: Callable) -> None:
    """Attach the safe Xavani Console REPL subcommand."""
    console_parser = subparsers.add_parser(
        "console",
        help="Open the safe Xavani command console",
        description=(
            "Open a curated Xavani command REPL. This is not a raw shell and "
            "does not expose the full Xavani CLI."
        ),
    )
    console_parser.set_defaults(func=cmd_console)
