# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Undo journal for file writes.

Captures prior file content before a write tool mutates a path and stores
it in a JSONL journal under ``~/.xavani/write_journal/journal.jsonl``.
Rollback restores the captured bytes, or deletes files that did not exist
before the write. The journal keeps at most ``_MAX_ENTRIES`` entries.
"""

import base64
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

_MAX_ENTRIES = 50

_lock = threading.Lock()


def journal_dir() -> Path:
    override = os.environ.get("XAVANI_WRITE_JOURNAL_DIR")
    if override:
        return Path(override)
    return Path.home() / ".xavani" / "write_journal"


def _journal_file(directory: Optional[Path] = None) -> Path:
    return (directory or journal_dir()) / "journal.jsonl"


def capture(path: str) -> dict:
    resolved = Path(path).expanduser()
    try:
        data = resolved.read_bytes()
        entry = {"path": str(resolved), "existed": True, "data_b64": base64.b64encode(data).decode("ascii")}
    except FileNotFoundError:
        entry = {"path": str(resolved), "existed": False, "data_b64": None}
    except OSError:
        entry = {"path": str(resolved), "existed": False, "data_b64": None}
    entry["captured"] = True
    return entry


def commit(entry: dict, directory: Optional[Path] = None) -> bool:
    if not entry.get("captured"):
        return False
    target = _journal_file(directory)
    record = {
        "ts": time.time(),
        "path": entry["path"],
        "existed": entry["existed"],
        "data_b64": entry["data_b64"],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        lines = _read_lines(target)
        lines.append(record)
        if len(lines) > _MAX_ENTRIES:
            lines = lines[-_MAX_ENTRIES:]
            _write_lines(target, lines)
        else:
            with open(target, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


def discard(entry: dict) -> None:
    entry.pop("captured", None)


def rollback_last(count: int = 1, directory: Optional[Path] = None) -> list:
    """Restore the last ``count`` journaled writes. Returns summaries."""
    if count < 1:
        raise ValueError("count must be >= 1")
    target = _journal_file(directory)
    restored = []
    with _lock:
        lines = _read_lines(target)
        take = lines[-count:]
        keep = lines[:-count] if count < len(lines) else []
        for record in reversed(take):
            restored.append(_restore(record))
        _write_lines(target, keep)
    return restored


def _restore(record: dict) -> str:
    path = Path(record["path"])
    if record["existed"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = base64.b64decode(record["data_b64"])
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".wj-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return f"restored {path}"
    try:
        path.unlink()
        return f"deleted {path} (file did not exist before the write)"
    except FileNotFoundError:
        return f"skipped {path} (already gone)"


def _read_lines(target: Path) -> list:
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    lines = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return lines


def _write_lines(target: Path, records: list) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), prefix=".journal-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
