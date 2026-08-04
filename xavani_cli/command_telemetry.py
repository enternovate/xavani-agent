# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D02: dangerous-command telemetry.

Aggregates the approval reasoning log (D09) into security telemetry:

- which commands trigger guards, and how often
- approve / deny / timeout rates per reason category
- most-common dangerous patterns

This answers "is the hardening working?" with numbers instead of vibes.
The source of truth is the D09 JSONL trail — no new recording surface.

Usage::

    from xavani_cli.command_telemetry import telemetry_report

    report = telemetry_report()
    print(report["overall"]["deny_rate"])
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_HOURS = 24


def _reason_log_path() -> Path:
    home = Path(os.environ.get("XAVANI_HOME", "~/.xavani")).expanduser()
    return home / "data" / "approval_reasoning.jsonl"


def load_entries(hours: Optional[float] = None, limit: int = 100_000) -> List[Dict[str, Any]]:
    """Load D09 reasoning entries within the window, newest first."""
    hours = hours if hours is not None else DEFAULT_HOURS
    cutoff = time.time() - hours * 3600
    path = _reason_log_path()
    entries: List[Dict[str, Any]] = []
    try:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("ts", 0) < cutoff:
                    continue
                entries.append(record)
    except OSError:
        return []
    return entries


def telemetry_report(hours: Optional[float] = None) -> Dict[str, Any]:
    """Aggregate the reasoning log into a telemetry report."""
    entries = load_entries(hours)

    total = len(entries)
    decision_counts = Counter(e.get("decision") for e in entries)
    reason_counts = Counter(e.get("reason") for e in entries)
    pattern_counts = Counter(e.get("pattern_key") for e in entries if e.get("pattern_key"))
    by_reason: Dict[str, Dict[str, int]] = defaultdict(lambda: {"allow": 0, "deny": 0, "timeout": 0, "ask": 0})
    for e in entries:
        reason = e.get("reason") or "unknown"
        decision = e.get("decision") or "unknown"
        by_reason[reason][decision] = by_reason[reason].get(decision, 0) + 1

    deny_total = decision_counts.get("deny", 0)
    allow_total = decision_counts.get("allow", 0)
    return {
        "window_hours": hours if hours is not None else DEFAULT_HOURS,
        "total_decisions": total,
        "decisions": dict(decision_counts),
        "deny_rate": round(deny_total / total, 4) if total else 0.0,
        "allow_rate": round(allow_total / total, 4) if total else 0.0,
        "top_reasons": dict(reason_counts.most_common(10)),
        "top_patterns": dict(pattern_counts.most_common(10)),
        "by_reason": {k: dict(v) for k, v in sorted(by_reason.items())},
    }


def format_telemetry_report(report: Dict[str, Any]) -> str:
    """Render the report as a compact console block."""
    lines = [
        f"Command telemetry (last {report['window_hours']}h): "
        f"{report['total_decisions']} decisions",
        f"  deny rate: {report['deny_rate']:.1%}  allow rate: {report['allow_rate']:.1%}",
        f"  decisions: {report['decisions']}",
    ]
    if report["top_reasons"]:
        lines.append("  by reason:")
        for reason, count in report["top_reasons"].items():
            lines.append(f"    {reason:<16} {count}")
    if report["top_patterns"]:
        lines.append("  top patterns:")
        for pattern, count in report["top_patterns"].items():
            lines.append(f"    {pattern:<40} {count}")
    return "\n".join(lines)
