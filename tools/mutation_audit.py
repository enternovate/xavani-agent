"""Append-only JSONL audit of memory and skill mutations (D06).

Every memory/skill write is appended to ``<XAVANI_HOME>/logs/mutation_audit.jsonl``
with its origin (assistant_tool vs background_review) so mutations are
traceable end-to-end. No plaintext secrets are stored: only the target
name, action, and a truncated preview are recorded. Write failures fail
open — an audit must never break a memory or skill write.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

from tools.skill_provenance import get_current_write_origin

logger = logging.getLogger(__name__)

_AUDIT_FILE_NAME = "mutation_audit.jsonl"
_PREVIEW_LEN = 200
_lock = threading.Lock()


def audit_path(xavani_home: Optional[str] = None) -> str:
    """Resolve the audit log path under the given (or default) home."""
    home = xavani_home or os.environ.get("XAVANI_HOME", "") or os.path.expanduser("~/.xavani")
    return os.path.join(home, "logs", _AUDIT_FILE_NAME)


def log_mutation(
    kind: str,
    action: str,
    target: str,
    *,
    content: Optional[str] = None,
    origin: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one mutation record. Never raises.

    Args:
        kind: "memory" or "skill".
        action: add/replace/remove/create/edit/patch/delete/write_file/remove_file.
        target: store target (memory target / skill name).
        content: optional preview text (truncated, never full secrets).
        origin: write origin; defaults to the provenance ContextVar.
        extra: optional extra fields (e.g. {"success": True}).
    """
    try:
        record = {
            "ts": time.time(),
            "kind": kind,
            "action": action,
            "target": str(target)[:200],
            "origin": origin or get_current_write_origin() or "assistant_tool",
        }
        if content:
            preview = content if isinstance(content, str) else str(content)
            record["preview"] = preview[:_PREVIEW_LEN]
        if extra:
            record.update(extra)
        path = audit_path()
        with _lock:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("mutation audit write failed: %s", exc)


def read_audit(xavani_home: Optional[str] = None) -> list[Dict[str, Any]]:
    """Read all audit records (for tooling/tests). Missing file -> []."""
    path = audit_path(xavani_home)
    records = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return records


__all__ = ["log_mutation", "read_audit", "audit_path"]
