# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tool-call quality metrics (harness item 2, HARNESS_UPGRADES_0115.md).

Records one row per tool call: tool name, latency ms, success, retry
count, error class. Exports per-session CSV/JSONL and aggregates for the
``xavani stats`` surface. Pure module — the conversation loop calls
:func:`record_call` at dispatch boundaries.
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ToolCallRecord:
    """One tool invocation."""
    tool: str
    started_at: float
    latency_ms: float
    success: bool
    retries: int = 0
    error_class: str = ""
    session_id: str = ""


def _metrics_dir() -> Path:
    """Return the metrics storage directory under the Xavani home."""
    from xavani_constants import get_xavani_home

    d = get_xavani_home() / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _jsonl_path(session_id: str) -> Path:
    """Return the per-session JSONL path."""
    safe = session_id.replace("/", "_").replace("\\", "_") or "unknown"
    return _metrics_dir() / f"tool-calls-{safe}.jsonl"


def _csv_path(session_id: str) -> Path:
    """Return the per-session CSV path."""
    safe = session_id.replace("/", "_").replace("\\", "_") or "unknown"
    return _metrics_dir() / f"tool-calls-{safe}.csv"


def record_call(record: ToolCallRecord) -> None:
    """Append one tool-call record to the session JSONL (and CSV)."""
    payload = asdict(record)
    path = _jsonl_path(record.session_id)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")

    csv_path = _csv_path(record.session_id)
    fresh = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(payload.keys()))
        if fresh:
            writer.writeheader()
        writer.writerow(payload)


def load_session(session_id: str) -> List[ToolCallRecord]:
    """Load all recorded calls for one session."""
    path = _jsonl_path(session_id)
    if not path.exists():
        return []
    out: List[ToolCallRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(ToolCallRecord(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue
    return out


def aggregate(calls: List[ToolCallRecord]) -> Dict[str, Any]:
    """Summarise calls per tool: count, success rate, latency, retries."""
    by_tool: Dict[str, List[ToolCallRecord]] = {}
    for call in calls:
        by_tool.setdefault(call.tool, []).append(call)

    rows = []
    for tool, group in sorted(by_tool.items()):
        ok = sum(1 for c in group if c.success)
        rows.append(
            {
                "tool": tool,
                "calls": len(group),
                "success_rate": round(ok / len(group), 4) if group else 0.0,
                "avg_latency_ms": round(sum(c.latency_ms for c in group) / len(group), 2) if group else 0.0,
                "total_retries": sum(c.retries for c in group),
            }
        )
    return {
        "total_calls": len(calls),
        "total_success": sum(1 for c in calls if c.success),
        "total_retries": sum(c.retries for c in calls),
        "per_tool": rows,
    }


def format_stats(calls: List[ToolCallRecord]) -> str:
    """Render a human-readable stats block for ``xavani stats``."""
    agg = aggregate(calls)
    lines = [f"Tool calls: {agg['total_calls']} (success {agg['total_success']}, retries {agg['total_retries']})"]
    for row in agg["per_tool"]:
        lines.append(
            f"  {row['tool']}: {row['calls']} calls, {row['success_rate'] * 100:.1f}% ok, "
            f"avg {row['avg_latency_ms']:.0f}ms, {row['total_retries']} retries"
        )
    return "\n".join(lines)
