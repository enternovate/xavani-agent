#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Persistent Todo Store — survives sessions in the profile home.

Extends the in-memory TodoStore with JSON persistence at
``$XAVANI_HOME/todos.json``. List order is priority (same semantics as
the engine todo tool). Writes are atomic (tempfile + os.replace) and the
file keeps mode 0600 so task contents stay private.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.todo_tool import VALID_STATUSES, TodoStore

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME") or Path.home() / ".xavani")
DEFAULT_PATH = XAVANI_HOME / "todos.json"

_ITEM_EXTRA_FIELDS = ("priority", "created", "updated", "source_session")


class PersistentTodoStore(TodoStore):
    """TodoStore that loads from and saves to a JSON file."""

    def __init__(self, path: Optional[Path] = None) -> None:
        super().__init__()
        self.path = Path(path) if path else DEFAULT_PATH
        self._items = self._load()

    # -- loading ------------------------------------------------------------

    def _load(self) -> List[Dict[str, str]]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return []
        try:
            payload = json.loads(raw)
        except ValueError:
            return []
        items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return []
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            clean = self._validate(item)
            for field in _ITEM_EXTRA_FIELDS:
                if item.get(field) is not None:
                    clean[field] = item[field]
            out.append(clean)
        return out

    def reload(self) -> List[Dict[str, str]]:
        """Discard in-memory state and re-read from disk."""
        self._items = self._load()
        return self.read()

    # -- saving ---------------------------------------------------------------

    def _save(self) -> None:
        payload = {"version": 1, "items": self.read()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=".todos-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, self.path)
        except OSError:
            with suppress_oserror():
                os.unlink(tmp_name)
            raise

    # -- overridden mutations -----------------------------------------------

    def write(
        self, todos: List[Dict[str, Any]], merge: bool = False
    ) -> List[Dict[str, str]]:
        result = super().write(todos, merge)
        self._save()
        return result

    def reorder(self, ordered_ids: List[str]) -> List[Dict[str, str]]:
        """Rewrite list order to match ordered_ids; unknown ids keep relative order at the end."""
        known = {item["id"]: item for item in self._items}
        reordered: List[Dict[str, str]] = []
        seen: set[str] = set()
        for item_id in ordered_ids:
            item = known.get(str(item_id))
            if item is not None and item["id"] not in seen:
                reordered.append(item)
                seen.add(item["id"])
        for item in self._items:
            if item["id"] not in seen:
                reordered.append(item)
                seen.add(item["id"])
        self._items = reordered
        self._save()
        return self.read()

    def set_status(self, item_id: str, status: str) -> Optional[Dict[str, str]]:
        """Set one item's status. Returns the updated item or None."""
        status = str(status).strip().lower()
        if status not in VALID_STATUSES:
            return None
        for item in self._items:
            if item["id"] == str(item_id):
                item["status"] = status
                self._save()
                return item.copy()
        return None


class suppress_oserror:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return exc_type is not None and issubclass(exc_type, OSError)
