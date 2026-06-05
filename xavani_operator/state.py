# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Persistent operator state store (v0.7.0 operator U3).

A tiny, dependency-free JSON document store under ``~/.xavani/operator/`` that the
loop, approval queue, and learn step build on. Documents are grouped into
*collections* (e.g. ``proposals``, ``cycles``, ``tasks``) and addressed by a safe
key; each is a single ``<collection>/<key>.json`` file written atomically
(temp + ``os.replace``) so a crash mid-write never corrupts state.

Pure local I/O — **no LLM, no network** (R10). Keys are validated to block path
traversal: state never escapes the operator directory.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_RESERVED = {".", ".."}


def _xavani_home() -> Path:
    """Active XAVANI_HOME (profile-aware), mirroring ``agent.file_safety``."""
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home()
    except Exception:
        return Path(os.path.expanduser("~/.xavani"))


def default_operator_dir() -> Path:
    """The default operator state directory: ``<xavani-home>/operator``."""
    return _xavani_home() / "operator"


def _check_name(name: str, what: str) -> str:
    """Reject empty, reserved, or traversal-prone collection/key names."""
    if not name or name in _RESERVED or not _SAFE_NAME.match(name):
        raise ValueError(f"unsafe operator {what}: {name!r}")
    return name


class OperatorState:
    """A JSON document store rooted at ``root`` (defaults to the operator dir)."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_operator_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, collection: str, key: str) -> Path:
        _check_name(collection, "collection")
        _check_name(key, "key")
        return self.root / collection / f"{key}.json"

    def put(self, collection: str, key: str, value: dict[str, Any]) -> None:
        """Store ``value`` (a JSON-serialisable dict) atomically."""
        path = self._path_for(collection, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(value, fh, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def get(self, collection: str, key: str) -> dict[str, Any] | None:
        """Return the stored dict, or ``None`` if absent."""
        path = self._path_for(collection, key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self, collection: str) -> list[dict[str, Any]]:
        """Return every document in ``collection``, ordered by key (stable)."""
        _check_name(collection, "collection")
        cdir = self.root / collection
        if not cdir.exists():
            return []
        return [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(cdir.glob("*.json"))
        ]

    def delete(self, collection: str, key: str) -> bool:
        """Delete a document; return ``True`` if it existed."""
        path = self._path_for(collection, key)
        if not path.exists():
            return False
        path.unlink()
        return True
