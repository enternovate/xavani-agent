# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""``xavani tokens`` — one credential vault for all products (Task 6.1).

Stores API tokens in ``~/.xavani/credentials.json`` with 0600 permissions.
Products read tokens from here; ``xavani doctor`` validates them. Values
are never printed back. No telemetry.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def credentials_path() -> Path:
    """Return the credentials vault path under the Xavani home."""
    from xavani_constants import get_xavani_home

    return get_xavani_home() / "credentials.json"


def _ensure_0600(path: Path) -> None:
    """Restrict the vault to the owner (POSIX only)."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _load() -> Dict[str, Any]:
    """Load the vault; return {} when missing or corrupt."""
    path = credentials_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, Any]) -> None:
    """Write the vault atomically with 0600 perms."""
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _ensure_0600(tmp)
    tmp.replace(path)
    _ensure_0600(path)


def token_add(name: str, value: str, *, provider: str = "") -> None:
    """Store a token.  Raises ValueError on invalid input."""
    name = name.strip()
    if not name:
        raise ValueError("token name is required")
    if not value.strip():
        raise ValueError("token value is required")
    data: Dict[str, Any] = _load()
    entry = data.get(name, {})
    if isinstance(entry, str):
        entry = {"value": entry}
    entry = dict(entry)
    entry["value"] = value.strip()
    entry["updated_at"] = time.time()
    if provider:
        entry["provider"] = provider
    data[name] = entry
    _save(data)
    print(f"\u2713 Token '{name}' saved ({len(value.strip())} chars).")


def token_list() -> List[Dict[str, Any]]:
    """Return token metadata (never values)."""
    out: List[Dict[str, Any]] = []
    for name, entry in _load().items():
        meta: Dict[str, Any] = {"name": name}
        if isinstance(entry, dict):
            meta["provider"] = entry.get("provider", "")
            meta["updated_at"] = entry.get("updated_at")
            meta["length"] = len(str(entry.get("value", "")))
        else:
            meta["length"] = len(str(entry))
        out.append(meta)
    return sorted(out, key=lambda m: str(m["name"]))


def token_remove(name: str) -> bool:
    """Remove a token.  Returns True when it existed."""
    data = _load()
    if name not in data:
        return False
    del data[name]
    _save(data)
    return True


def token_get(name: str) -> Optional[str]:
    """Return the raw token value (for integrations), or None."""
    entry = _load().get(name)
    if isinstance(entry, dict):
        value = entry.get("value")
        return str(value) if value else None
    return str(entry) if entry else None


def token_usage() -> Dict[str, Any]:
    """Summarise vault usage for ``show-usage`` / ``doctor``."""
    entries = token_list()
    return {
        "total": len(entries),
        "tokens": entries,
        "path": str(credentials_path()),
        "has_provider_keys": any(e.get("provider") for e in entries),
    }


def cmd_tokens(args) -> None:
    """Argparse entry point for the ``tokens`` command."""
    action = getattr(args, "tokens_command", None) or "list"
    if action == "add":
        name = getattr(args, "name", "")
        value = getattr(args, "value", "")
        provider = getattr(args, "provider", "") or ""
        try:
            token_add(name, value, provider=provider)
        except ValueError as exc:
            print(f"\u2717 {exc}")
            sys.exit(2)
    elif action == "remove":
        name = getattr(args, "name", "")
        if token_remove(name):
            print(f"\u2713 Token '{name}' removed.")
        else:
            print(f"\u2717 Token '{name}' not found.")
            sys.exit(1)
    elif action == "show-usage":
        usage = token_usage()
        print(f"Vault: {usage['path']}")
        print(f"Tokens: {usage['total']}")
        for entry in usage["tokens"]:
            provider = f" ({entry['provider']})" if entry.get("provider") else ""
            print(f"  {entry['name']}{provider} — {entry['length']} chars")
    else:
        for entry in token_list():
            provider = f" ({entry['provider']})" if entry.get("provider") else ""
            print(f"{entry['name']}{provider}")


def validate_tokens() -> List[str]:
    """Return problems found by ``xavani doctor`` (empty = healthy)."""
    problems = []
    path = credentials_path()
    if path.exists():
        try:
            mode = path.stat().st_mode & 0o777
            if mode != 0o600:
                problems.append(f"credentials vault permissions are {oct(mode)}, expected 0600: {path}")
        except OSError as exc:
            problems.append(f"cannot stat credentials vault: {exc}")
    for entry in token_list():
        if not entry.get("length"):
            problems.append(f"token '{entry['name']}' is empty")
    return problems
