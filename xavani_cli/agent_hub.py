# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Agent hub roster: list, steer, kill, and revive subagents.

Backed by tools.delegate_tool's live subagent registry. Kill parks the
child's goal so /hub revive can re-spawn it through delegate_task.
"""

import threading
import time
from typing import Any, Dict, List

_parked_lock = threading.Lock()
_parked: Dict[str, Dict[str, Any]] = {}


def roster() -> List[Dict[str, Any]]:
    """Live children with computed duration; copies, no agent refs."""
    from tools.delegate_tool import list_active_subagents

    now = time.time()
    rows = []
    for record in list_active_subagents():
        row = dict(record)
        row["duration_s"] = round(now - float(record.get("started_at", now)), 1)
        row["cost_usd"] = record.get("cost_usd")
        rows.append(row)
    return rows


def steer(subagent_id: str, text: str) -> bool:
    """Inject a course-correction message into a running child."""
    if not text or not text.strip():
        return False
    from tools.delegate_tool import _active_subagents, _active_subagents_lock

    with _active_subagents_lock:
        record = _active_subagents.get(subagent_id)
    agent = record.get("agent") if record else None
    if agent is None:
        return False
    try:
        return bool(agent.steer(text.strip()))
    except Exception:
        return False


def kill(subagent_id: str) -> Dict[str, Any]:
    """Interrupt one child without touching the parent; park its goal."""
    from tools.delegate_tool import interrupt_subagent, list_active_subagents

    goal = None
    for record in list_active_subagents():
        if record.get("subagent_id") == subagent_id:
            goal = record.get("goal")
            break
    stopped = interrupt_subagent(subagent_id)
    if stopped and goal:
        with _parked_lock:
            _parked[subagent_id] = {
                "subagent_id": subagent_id,
                "goal": goal,
                "parked_at": time.time(),
            }
    return {"ok": stopped, "subagent_id": subagent_id}


def parked() -> List[Dict[str, Any]]:
    """Children killed via the hub and eligible for revive."""
    with _parked_lock:
        return [dict(v) for v in _parked.values()]


def revive(subagent_id: str, parent_agent: Any) -> Dict[str, Any]:
    """Re-spawn a parked child through delegate_task with its old goal."""
    with _parked_lock:
        snapshot = _parked.pop(subagent_id, None)
    if not snapshot:
        return {"ok": False, "error": f"no parked child {subagent_id}"}
    try:
        from tools.delegate_tool import delegate_task

        result = delegate_task(goal=snapshot["goal"], parent_agent=parent_agent)
    except Exception as exc:
        with _parked_lock:
            _parked[subagent_id] = snapshot
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "result": result}
