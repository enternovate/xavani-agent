# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""E05: per-session token/cost rows as CSV for accounting.

``sessions_to_csv`` renders exported session dicts (from
``SessionDB.export_session`` / ``export_all``) as a CSV with one row per
session: identity columns plus estimated/actual cost and cost status.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

_COLUMNS = [
    "session_id",
    "title",
    "source",
    "model",
    "platform",
    "started_at",
    "last_active",
    "estimated_cost_usd",
    "actual_cost_usd",
    "cost_status",
    "cost_source",
]

# Session dicts produced by ``SessionDB.export_session`` / ``export_all``
# (and by ``search_sessions``) use the DB column name ``id``; the CSV
# column is ``session_id``.  Alias so the identity column is never blank.
_KEY_ALIASES = {
    "session_id": "id",
}


def _value(session: Dict[str, Any], key: str) -> Any:
    value = session.get(key, "")
    if value in (None, "") and key in _KEY_ALIASES:
        value = session.get(_KEY_ALIASES[key], "")
    if value is None:
        return ""
    if key.endswith("_cost_usd") and isinstance(value, (int, float)):
        return round(float(value), 6)
    return value


def sessions_to_csv(sessions: List[Dict[str, Any]]) -> str:
    """Render exported sessions as CSV text (header + one row per session)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_COLUMNS)
    for session in sessions:
        if not isinstance(session, dict):
            continue
        writer.writerow([_value(session, col) for col in _COLUMNS])
    return buffer.getvalue()


__all__ = ["sessions_to_csv", "_COLUMNS"]
