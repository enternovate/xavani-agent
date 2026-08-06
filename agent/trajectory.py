# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Trajectory saving utilities and static helpers.

_convert_to_trajectory_format stays as an AIAgent method (batch_runner.py
calls agent._convert_to_trajectory_format). Only the static helpers and
the file-write logic live here.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


def convert_scratchpad_to_think(content: str) -> str:
    """Convert <REASONING_SCRATCHPAD> tags to <think> tags."""
    if not content or "<REASONING_SCRATCHPAD>" not in content:
        return content
    return content.replace("<REASONING_SCRATCHPAD>", "<think>").replace("</REASONING_SCRATCHPAD>", "</think>")


def has_incomplete_scratchpad(content: str) -> bool:
    """Check if content has an opening <REASONING_SCRATCHPAD> without a closing tag."""
    if not content:
        return False
    return "<REASONING_SCRATCHPAD>" in content and "</REASONING_SCRATCHPAD>" not in content


def save_trajectory(trajectory: List[Dict[str, Any]], model: str,
                    completed: bool, filename: str = None):
    """Append a trajectory entry to a JSONL file.

    Args:
        trajectory: The ShareGPT-format conversation list.
        model: Model name for metadata.
        completed: Whether the conversation completed successfully.
        filename: Override output filename. Defaults to trajectory_samples.jsonl
                  or failed_trajectories.jsonl based on ``completed``.
    """
    if filename is None:
        filename = "trajectory_samples.jsonl" if completed else "failed_trajectories.jsonl"

    entry = {
        "conversations": trajectory,
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "completed": completed,
    }

    try:
        from agent.redact import redact_sensitive_text
        safe_entry = json.loads(redact_sensitive_text(json.dumps(entry, ensure_ascii=False)))
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(safe_entry, ensure_ascii=False) + "\n")  # nosec B105 - already redacted before write
        logger.info("Trajectory saved to %s", filename)
    except Exception as e:
        logger.warning("Failed to save trajectory: %s", e)


# ── E02: per-turn timeline trace ────────────────────────────────

def turn_timeline_path() -> str:
    """Path of the per-turn timeline JSONL under the Xavani home."""
    from xavani_constants import get_xavani_home

    logs_dir = get_xavani_home() / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return str(logs_dir / "turn_timeline.jsonl")


# Keys that may carry credentials are replaced whole, not just scrubbed.
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(token|secret|passwd|password|api[_-]?key|authorization|cookie|credential)"
)


def _sanitize_timeline_value(value: Any) -> Any:
    """Recursively redact credentials in a timeline record before storage."""
    if isinstance(value, str):
        from agent.redact import redact_sensitive_text

        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {
            key: "<redacted>"
            if _SENSITIVE_KEY_RE.search(key)
            else _sanitize_timeline_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_timeline_value(item) for item in value]
    return value


def record_turn_timeline(entry: Dict[str, Any]) -> bool:
    """Append one per-turn trace record (E02). Best-effort; never raises.

    The record carries the user message, model call count, tool call
    count, final response snippet, exit reason and duration so a
    debugging session can answer "why did the agent do X".
    """
    try:
        record = dict(entry)
        record.setdefault("timestamp", datetime.now().isoformat())
        safe = _sanitize_timeline_value(record)
        with open(turn_timeline_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=False) + "\n")
        return True
    except Exception as exc:
        logger.warning("Failed to record turn timeline: %s", exc)
        return False


def load_turn_timeline(limit: int = 100) -> List[Dict[str, Any]]:
    """Read the most recent turn-timeline records, newest first."""
    records: List[Dict[str, Any]] = []
    try:
        with open(turn_timeline_path(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return records[-limit:][::-1]
