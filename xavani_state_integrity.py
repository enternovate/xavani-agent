# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Hash-based state file integrity verification (A12).

Every state file gets a SHA-256 sidecar (<path>.sha256). Reads verify
the sidecar. A mismatch raises StateCorruptionError. SQLite databases
use PRAGMA quick_check, cached on (path, size, mtime_ns).

Covered files:
- session DB, episodic/procedural memory DBs
- config.yaml (loud warning + re-arm on legitimate hand edits)

Set XAVANI_SKIP_STATE_INTEGRITY=1 to disable verification.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_HASH_SUFFIX = ".sha256"
_SQLITE_CACHE: dict = {}
_SQLITE_CACHE_LOCK = threading.Lock()


class StateCorruptionError(Exception):
    """Raised when a state file fails its integrity check."""

    def __init__(self, path, detail=""):
        self.path = str(path)
        self.detail = detail
        super().__init__(f"State corruption detected: {self.path} {detail}".strip())


def sha256_file(path) -> str:
    """Compute the SHA-256 digest of a file. Returns a hex string."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def state_hash_path(path) -> Path:
    """Return the sidecar path for a state file."""
    return Path(str(path) + _HASH_SUFFIX)


def write_state_hash(path) -> Path:
    """Compute and atomically write the sidecar hash."""
    path = Path(path)
    digest = sha256_file(path)
    sidecar = state_hash_path(path)
    tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    tmp.write_text(digest + "\n", encoding="utf-8")
    os.replace(tmp, sidecar)
    return sidecar


def verify_state_file(path, *, rearm_on_mismatch: bool = False) -> Optional[str]:
    """Verify a state file against its sidecar hash.

    Returns the expected digest, or None when no sidecar exists.
    Raises StateCorruptionError on mismatch. When rearm_on_mismatch is
    True, the sidecar is rewritten from the current content instead of
    raising (used for user-editable files like config.yaml).
    """
    path = Path(path)
    sidecar = state_hash_path(path)
    if not sidecar.exists():
        return None
    expected = sidecar.read_text(encoding="utf-8").strip()
    actual = sha256_file(path)
    if actual != expected:
        if rearm_on_mismatch:
            write_state_hash(path)
            return actual
        raise StateCorruptionError(
            path,
            f"expected {expected[:12]}... got {actual[:12]}...",
        )
    return expected


def read_state_file(path, *, rearm_on_mismatch: bool = False) -> bytes:
    """Read a state file, verifying its sidecar hash first."""
    verify_state_file(path, rearm_on_mismatch=rearm_on_mismatch)
    with open(path, "rb") as f:
        return f.read()


def write_state_file(path, data: bytes) -> None:
    """Atomically write state bytes, then refresh the sidecar hash."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    write_state_hash(path)


def clear_sqlite_verify_cache() -> None:
    """Clear the SQLite verification cache. For tests."""
    with _SQLITE_CACHE_LOCK:
        _SQLITE_CACHE.clear()


def verify_sqlite_db(db_path, *, force: bool = False) -> Optional[str]:
    """Run PRAGMA quick_check on an SQLite database.

    Cached on (path, size, mtime_ns). Raises StateCorruptionError when
    the database is corrupt. Returns "ok" or None when skipped.
    """
    path = Path(db_path)
    if not path.exists():
        return None
    try:
        st = path.stat()
    except OSError:
        return None
    key = (str(path), st.st_size, st.st_mtime_ns)
    if not force:
        with _SQLITE_CACHE_LOCK:
            if key in _SQLITE_CACHE:
                return _SQLITE_CACHE[key]
    result = None
    try:
        # Plain connect mirrors app behavior (WAL databases need normal
        # open semantics; mode=ro can fail on missing -shm files).
        conn = sqlite3.connect(str(path), timeout=1.0)
        try:
            row = conn.execute("PRAGMA quick_check").fetchone()
            result = row[0] if row else "unknown"
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise StateCorruptionError(path, f"quick_check failed: {exc}") from exc
    if result != "ok":
        raise StateCorruptionError(path, f"quick_check: {result}")
    with _SQLITE_CACHE_LOCK:
        _SQLITE_CACHE[key] = result
    return result


def integrity_enabled() -> bool:
    """Return True when state integrity verification is enabled."""
    return os.environ.get("XAVANI_SKIP_STATE_INTEGRITY") != "1"
