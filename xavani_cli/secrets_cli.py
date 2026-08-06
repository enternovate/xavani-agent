# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Secrets vault CLI (C04).

A minimal vault for API keys and other secrets.  Secrets live in
``~/.xavani/.env`` — the same store the rest of the CLI reads at
startup.  Values are written once and never printed back.
"""

from __future__ import annotations

import sys
from typing import List

from xavani_cli.config import load_env, remove_env_value, save_env_value


def secrets_add(name: str, value: str) -> None:
    """Store a secret.  Raises ValueError on an invalid name."""
    save_env_value(name, value)
    print(f"\u2713 Secret '{name}' saved.")


def secrets_list() -> List[str]:
    """Return sorted secret names.  Values stay hidden."""
    return sorted(load_env().keys())


def secrets_remove(name: str) -> bool:
    """Remove a secret.  Returns True when it existed."""
    return remove_env_value(name)


def cmd_secrets(args) -> None:
    """Argparse entry point for the ``secrets`` command."""
    action = getattr(args, "secrets_command", None) or "list"
    if action == "add":
        if not getattr(args, "name", None) or getattr(args, "value", None) is None:
            print("\u2717 Usage: xavani secrets add NAME VALUE")
            sys.exit(2)
        secrets_add(args.name, args.value)
    elif action == "remove":
        if not getattr(args, "name", None):
            print("\u2717 Usage: xavani secrets remove NAME")
            sys.exit(2)
        if secrets_remove(args.name):
            print(f"\u2713 Secret '{args.name}' removed.")
        else:
            print(f"\u2717 Secret '{args.name}' not found.")
            sys.exit(1)
    else:
        # Names only. Secret VALUES are never printed or logged.
        for name in secrets_list():
            print(name)
