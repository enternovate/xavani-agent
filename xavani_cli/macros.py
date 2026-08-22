# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic macro slash commands: /macro define|run|list|remove.

A macro is a named sequence of prompt steps stored as JSON under
``~/.xavani/macros/``. Running a macro returns its steps verbatim —
no model interpretation at definition or run time.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class MacroError(ValueError):
    pass


def macros_dir() -> Path:
    override = os.environ.get("XAVANI_MACROS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".xavani" / "macros"


def _path(name: str, directory: Optional[Path] = None) -> Path:
    if not _NAME_RE.match(name):
        raise MacroError(
            f"invalid macro name {name!r}: use lowercase letters, digits, "
            "- or _ (max 32 chars)"
        )
    return (directory or macros_dir()) / f"{name}.json"


def define_macro(
    name: str,
    steps: List[str],
    *,
    directory: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Persist a macro; refuses to overwrite unless asked."""
    clean_steps = [s.strip() for s in steps if s and s.strip()]
    if not clean_steps:
        raise MacroError("a macro needs at least one non-empty step")
    path = _path(name, directory)
    if path.exists() and not overwrite:
        raise MacroError(f"macro {name!r} already exists (pass overwrite)")
    record = {"name": name, "steps": clean_steps}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def load_macro(name: str, *, directory: Optional[Path] = None) -> Dict[str, Any]:
    path = _path(name, directory)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise MacroError(f"no macro {name!r}") from None
    except json.JSONDecodeError as exc:
        raise MacroError(f"macro {name!r} corrupted: {exc}") from None
    if not isinstance(record.get("steps"), list) or not record["steps"]:
        raise MacroError(f"macro {name!r} has no steps")
    return record


def render_macro(name: str, *, directory: Optional[Path] = None) -> str:
    """Render the macro's steps as numbered prompt lines."""
    record = load_macro(name, directory=directory)
    return "\n".join(
        f"{i}. {step}" for i, step in enumerate(record["steps"], start=1)
    )


def list_macros(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    base = directory or macros_dir()
    if not base.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            out.append({
                "name": record.get("name", path.stem),
                "steps": len(record.get("steps", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return out


def remove_macro(name: str, *, directory: Optional[Path] = None) -> bool:
    path = _path(name, directory)
    if not path.exists():
        return False
    path.unlink()
    return True
