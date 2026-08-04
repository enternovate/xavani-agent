# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D11: audit trail for every skill modification.

Every skill write (create, edit, patch, write_file, remove_file, delete)
is appended to a JSONL audit trail with:

- timestamp
- action + skill name + target file
- SHA-256 of the file BEFORE the change (None for create/delete)
- SHA-256 of the file AFTER the change (None for delete)
- success flag

The before/after hashes let an auditor detect unauthorized changes:
any modification that bypasses skill_manage leaves no matching pair.

Best-effort by design — audit must never block a skill write. All
failures are logged and swallowed. Set XAVANI_SKILL_AUDIT=0 to disable.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_AUDIT_DIR = "data"
_AUDIT_FILE = "skill_audit.jsonl"


def _audit_path() -> Path:
    """Return the audit trail path under XAVANI_HOME."""
    home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return home / _AUDIT_DIR / _AUDIT_FILE


def skill_audit_enabled() -> bool:
    """True when the skill audit trail is enabled (default)."""
    return os.environ.get("XAVANI_SKILL_AUDIT") != "0"


def record_skill_change(
    action: str,
    name: str,
    file_path: Optional[str] = None,
    before_sha256: Optional[str] = None,
    after_sha256: Optional[str] = None,
    success: bool = True,
    message: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Append one skill-change record. Returns True when written.

    Never raises: audit is best-effort. Records go to
    ``<XAVANI_HOME>/data/skill_audit.jsonl``.
    """
    if not skill_audit_enabled():
        return False
    record = {
        "ts": time.time(),
        "action": action,
        "skill": name,
        "file": file_path,
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
        "success": bool(success),
        "message": (message or "")[:200],
    }
    if extra:
        record["extra"] = extra
    try:
        path = _audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError as exc:
        logger.warning("skill audit write failed: %s", exc)
        return False


def list_skill_audit(limit: int = 100) -> list[Dict[str, Any]]:
    """Read the audit trail, newest first. Never raises."""
    path = _audit_path()
    records: list[Dict[str, Any]] = []
    try:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("skill audit read failed: %s", exc)
        return []
    return list(reversed(records))[:limit]


def count_skill_audit() -> int:
    """Return the number of records in the audit trail. Never raises."""
    return len(list_skill_audit(limit=10**6))
