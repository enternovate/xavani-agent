# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D09: approval reasoning log.

Every approval decision — block, allow, ask, timeout — is appended to a
JSONL trail with the reasoning chain: decision, reason category,
pattern matched, description, session key, and a truncated command.
This makes security decisions explainable: an auditor can reconstruct
WHY a command was blocked or allowed.

Best-effort by design — logging must never break the approval flow.
All failures are logged and swallowed. Set XAVANI_APPROVAL_REASON_LOG=0
to disable.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_AUDIT_DIR = "data"
_AUDIT_FILE = "approval_reasoning.jsonl"


def _reason_path() -> Any:
    """Return the reasoning log path under XAVANI_HOME."""
    from pathlib import Path

    home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return home / _AUDIT_DIR / _AUDIT_FILE


def reasoning_enabled() -> bool:
    """True when the approval reasoning log is enabled (default)."""
    return os.environ.get("XAVANI_APPROVAL_REASON_LOG") != "0"


def record_approval_reasoning(
    decision: str,
    reason: str,
    command: str = "",
    pattern_key: Optional[str] = None,
    description: str = "",
    session_key: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Append one approval decision record. Returns True when written.

    Args:
        decision: The outcome — "allow", "deny", "ask", "timeout".
        reason: The decision category (hardline, yolo, smart, user, ...).
        command: The shell command (truncated to 200 chars).
        pattern_key: The matched danger pattern, if any.
        description: Human-readable description of the risk.
        session_key: The approval session the decision belongs to.
        extra: Optional additional reasoning factors.
    """
    if not reasoning_enabled():
        return False
    record = {
        "ts": time.time(),
        "decision": decision,
        "reason": reason,
        "command": (command or "")[:200],
        "pattern_key": pattern_key,
        "description": (description or "")[:300],
        "session_key": (session_key or "")[:64],
    }
    if extra:
        record["extra"] = extra
    try:
        path = _reason_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError as exc:
        logger.warning("approval reasoning log write failed: %s", exc)
        return False


def list_approval_reasoning(limit: int = 100) -> list[Dict[str, Any]]:
    """Read the reasoning log, newest first. Never raises."""
    path = _reason_path()
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
        logger.warning("approval reasoning log read failed: %s", exc)
        return []
    return list(reversed(records))[:limit]
