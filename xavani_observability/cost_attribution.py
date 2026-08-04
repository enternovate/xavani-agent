# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C05: cost attribution.

Attributes LLM call costs to sessions and tasks so the question "what
did this task actually cost?" has a real answer. The D04 cost guard
tracks the burn rate; this module tracks WHERE the money went.

Costs are recorded per (session_id, task_id, model) with timestamps;
the report aggregates by session and by task. Pure in-memory ledger —
no persistence (sessions are short-lived, and persistence invites
stale-data bugs).

Usage::

    from xavani_observability.cost_attribution import cost_ledger, record_attributed_cost

    record_attributed_cost(session_id="s1", task_id="t1", model="claude-opus", cost_usd=0.05)
    report = cost_ledger().report()
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

_lock = threading.Lock()
_ledger: List[Dict[str, Any]] = []  # one entry per recorded call


class CostLedger:
    """In-memory cost attribution ledger (thread-safe)."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(
        self,
        session_id: str,
        task_id: str,
        model: str,
        cost_usd: float,
        now: float | None = None,
    ) -> None:
        if cost_usd <= 0:
            return
        with self._lock:
            self._entries.append(
                {
                    "session_id": session_id,
                    "task_id": task_id,
                    "model": model,
                    "cost_usd": cost_usd,
                    "ts": now if now is not None else time.time(),
                }
            )

    def report(self, hours: float | None = None) -> Dict[str, Any]:
        """Aggregate costs by session and by task within the window."""
        cutoff = time.time() - hours * 3600 if hours else 0.0
        by_session: Dict[str, float] = {}
        by_task: Dict[str, float] = {}
        by_model: Dict[str, float] = {}
        total = 0.0
        count = 0
        with self._lock:
            for entry in self._entries:
                if entry["ts"] < cutoff:
                    continue
                session_id = entry["session_id"]
                task_id = entry["task_id"]
                model = entry["model"]
                cost = entry["cost_usd"]
                by_session[session_id] = by_session.get(session_id, 0.0) + cost
                task_key = f"{session_id}::{task_id}"
                by_task[task_key] = by_task.get(task_key, 0.0) + cost
                by_model[model] = by_model.get(model, 0.0) + cost
                total += cost
                count += 1
        return {
            "total_usd": round(total, 4),
            "calls": count,
            "by_session": {k: round(v, 4) for k, v in sorted(by_session.items(), key=lambda kv: -kv[1])},
            "by_task": {k: round(v, 4) for k, v in sorted(by_task.items(), key=lambda kv: -kv[1])},
            "by_model": {k: round(v, 4) for k, v in sorted(by_model.items(), key=lambda kv: -kv[1])},
        }

    def session_cost(self, session_id: str) -> float:
        """Total cost attributed to one session (all time)."""
        with self._lock:
            return round(
                sum(e["cost_usd"] for e in self._entries if e["session_id"] == session_id),
                4,
            )

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()


_ledger_instance: Optional[CostLedger] = None
_ledger_lock = threading.Lock()


def cost_ledger() -> CostLedger:
    """Return the process-wide cost ledger."""
    global _ledger_instance
    with _ledger_lock:
        if _ledger_instance is None:
            _ledger_instance = CostLedger()
        return _ledger_instance


def record_attributed_cost(
    session_id: str,
    task_id: str,
    model: str,
    cost_usd: float,
) -> None:
    """Record an attributed LLM call cost (C05)."""
    try:
        cost_ledger().record(session_id, task_id, model, cost_usd)
    except Exception:
        pass


def reset_cost_ledger() -> None:
    """Reset the process-wide ledger. For tests."""
    global _ledger_instance
    with _ledger_lock:
        _ledger_instance = None
