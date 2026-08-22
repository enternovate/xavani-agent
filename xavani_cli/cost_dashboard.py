# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Cost dashboard: per-session, per-day, and per-model cost tables.

Reads the ``sessions`` table of the Xavani state DB read-only. The
connection is injectable so tests run against a temp schema.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

_QUERY = (
    "SELECT id, model, started_at, estimated_cost_usd, "
    "input_tokens + output_tokens AS total_tokens "
    "FROM sessions ORDER BY started_at"
)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def collect_rows(db_path: Path) -> List[Dict[str, Any]]:
    """Every session's id/model/day/cost/tokens; corrupt DB yields []."""
    try:
        conn = _connect(db_path)
    except sqlite3.Error:
        return []
    try:
        try:
            rows = conn.execute(_QUERY).fetchall()
        except sqlite3.Error:
            return []
        return [
            {
                "id": r["id"],
                "model": r["model"] or "unknown",
                "started_at": r["started_at"] or "",
                "day": (r["started_at"] or "")[:10],
                "cost": float(r["estimated_cost_usd"] or 0.0),
                "tokens": int(r["total_tokens"] or 0),
            }
            for r in rows
        ]
    finally:
        conn.close()


def aggregate(rows: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, float]]:
    """Sum cost/tokens and count sessions grouped by any row key."""
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        bucket = out.setdefault(str(row[key]), {"sessions": 0, "cost": 0.0, "tokens": 0})
        bucket["sessions"] += 1
        bucket["cost"] += row["cost"]
        bucket["tokens"] += row["tokens"]
    return dict(sorted(out.items()))


def render(db_path: Path) -> str:
    """Render the three-table dashboard; friendly text when empty."""
    rows = collect_rows(db_path)
    if not rows:
        return "No session cost data yet."
    total_cost = sum(r["cost"] for r in rows)
    lines = [f"Sessions: {len(rows)}   Total cost: ${total_cost:.4f}", ""]

    lines.append("By model:")
    lines.append(f"  {'model':<28} {'sessions':>8} {'cost':>12} {'tokens':>12}")
    for key, bucket in aggregate(rows, "model").items():
        lines.append(
            f"  {key:<28} {bucket['sessions']:>8} "
            f"{bucket['cost']:>12.4f} {bucket['tokens']:>12}"
        )

    lines.append("")
    lines.append("By day:")
    lines.append(f"  {'day':<12} {'sessions':>8} {'cost':>12} {'tokens':>12}")
    for key, bucket in aggregate(rows, "day").items():
        lines.append(
            f"  {key:<12} {bucket['sessions']:>8} "
            f"{bucket['cost']:>12.4f} {bucket['tokens']:>12}"
        )

    lines.append("")
    lines.append("Last 5 sessions:")
    lines.append(f"  {'session':<24} {'model':<20} {'cost':>10}")
    for row in rows[-5:]:
        lines.append(
            f"  {str(row['id'])[:24]:<24} {row['model'][:20]:<20} {row['cost']:>10.4f}"
        )
    return "\n".join(lines)
