# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E09: LLM-as-debugger.

Packages failure context into a structured debugging brief that an LLM
can analyze. The brief includes the error, the relevant log tail,
recent tool calls, and the environment fingerprint. The module only
PREPARES the brief — it never calls an LLM itself. This keeps the
diagnostic input deterministic and cheap to test.

Usage::

    from xavani_observability.debug_brief import build_debug_brief

    brief = build_debug_brief(
        error="TimeoutError: read timed out",
        context={"tool": "terminal"},
        log_tail=["...last lines..."],
    )
"""

from __future__ import annotations

import json
import platform
import socket
import sys
import time
from typing import Any, Dict, List, Optional

MAX_LOG_TAIL = 50
MAX_CONTEXT_KEYS = 30


def _host_fingerprint() -> Dict[str, str]:
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"
    return {
        "hostname": hostname,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }


def _log_tail(logs: List[str], limit: int = MAX_LOG_TAIL) -> List[str]:
    if not logs:
        return []
    return [str(line) for line in logs[-limit:]]


def _trim_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not context:
        return {}
    trimmed = {}
    for i, (key, value) in enumerate(context.items()):
        if i >= MAX_CONTEXT_KEYS:
            break
        try:
            trimmed[str(key)] = str(value)[:2000]
        except Exception:
            trimmed[str(key)] = "<unserializable>"
    return trimmed


def build_debug_brief(
    error: str,
    *,
    context: Optional[Dict[str, Any]] = None,
    log_tail: Optional[List[str]] = None,
    traceback_text: str = "",
    task_id: str = "",
) -> Dict[str, Any]:
    """Build a structured debug brief for LLM analysis."""
    return {
        "error": str(error),
        "traceback": traceback_text[:20_000],
        "context": _trim_context(context),
        "log_tail": _log_tail(log_tail or []),
        "task_id": task_id,
        "environment": _host_fingerprint(),
        "generated_at": time.time(),
    }


def render_brief(brief: Dict[str, Any], max_log_lines: int = 30) -> str:
    """Render the brief as a prompt-ready text block."""
    lines = [
        "=== Debug Brief ===",
        f"Error: {brief['error']}",
    ]
    if brief.get("task_id"):
        lines.append(f"Task: {brief['task_id']}")
    if brief.get("traceback"):
        lines.append("Traceback:")
        lines.append(brief["traceback"][:5000])
    if brief.get("context"):
        lines.append("Context:")
        for key, value in list(brief["context"].items())[:15]:
            lines.append(f"  {key}: {value}")
    log_lines = brief.get("log_tail", [])
    if log_lines:
        lines.append("Log tail:")
        for line in log_lines[-max_log_lines:]:
            lines.append(f"  {line}")
    env = brief.get("environment", {})
    if env:
        lines.append(
            "Environment: "
            + ", ".join(f"{k}={v}" for k, v in env.items())
        )
    return "\n".join(lines)


def brief_to_json(brief: Dict[str, Any]) -> str:
    """JSON-serialize the brief for storage or API payloads."""
    return json.dumps(brief, default=str)
