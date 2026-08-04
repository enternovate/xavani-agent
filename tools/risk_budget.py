# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D03: per-agent risk budgets.

Each agent session gets a risk budget. Dangerous actions cost budget
weighted by their risk tier. When the budget is exhausted, even
previously-approved patterns require explicit approval again — bounded
blast radius instead of unlimited trust.

Deterministic and thread-safe. Budget state is per session_key, stored
in memory (sessions are short-lived). Configurable via
XAVANI_RISK_BUDGET (default 100).

Usage::

    from tools.risk_budget import risk_budget_for, RiskBudget

    budget = risk_budget_for(session_key)
    if budget.spend(tier_cost):
        # action allowed within budget
    else:
        # budget exhausted — require explicit approval
"""

from __future__ import annotations

import os
import threading
from typing import Dict, Optional

DEFAULT_BUDGET = 100.0

# Risk tier costs (approval.py classify_command_risk alignment):
# read-only ops cost nothing; dangerous commands cost by severity.
TIER_COSTS = {
    "low": 5.0,
    "medium": 15.0,
    "high": 40.0,
    "critical": 100.0,
}

_budgets: Dict[str, "RiskBudget"] = {}
_budgets_lock = threading.Lock()


class RiskBudget:
    """Per-session risk budget with tier-weighted spending."""

    def __init__(self, session_key: str, limit: float = DEFAULT_BUDGET):
        self.session_key = session_key
        self.limit = limit
        self._spent = 0.0
        self._lock = threading.Lock()

    def spend(self, cost: float) -> bool:
        """Charge ``cost`` against the budget.

        Returns True when the charge was accepted (budget not
        exhausted). Returns False when the budget cannot cover the
        cost — the caller must require explicit approval.
        """
        with self._lock:
            if self._spent + cost > self.limit:
                return False
            self._spent += cost
            return True

    def remaining(self) -> float:
        """Budget left (0.0 when exhausted)."""
        with self._lock:
            return max(0.0, self.limit - self._spent)

    def exhausted(self) -> bool:
        """True when no budget remains."""
        return self.remaining() <= 0.0

    def reset(self) -> None:
        """Restore the full budget (new session, user opt-in)."""
        with self._lock:
            self._spent = 0.0

    def snapshot(self) -> Dict[str, float]:
        """Serializable view for dashboards and reasoning logs."""
        with self._lock:
            return {
                "limit": self.limit,
                "spent": round(self._spent, 2),
                "remaining": round(max(0.0, self.limit - self._spent), 2),
                "exhausted": self._spent >= self.limit,
            }


def configured_budget_limit() -> float:
    """Resolve the global budget limit from XAVANI_RISK_BUDGET."""
    raw = os.environ.get("XAVANI_RISK_BUDGET", str(DEFAULT_BUDGET))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return DEFAULT_BUDGET


def risk_budget_for(session_key: str) -> RiskBudget:
    """Return (creating if needed) the budget for a session key."""
    with _budgets_lock:
        budget = _budgets.get(session_key)
        if budget is None:
            budget = RiskBudget(session_key, configured_budget_limit())
            _budgets[session_key] = budget
        return budget


def reset_budget(session_key: str) -> None:
    """Reset a session's budget (new turn, explicit opt-in)."""
    with _budgets_lock:
        budget = _budgets.get(session_key)
        if budget is not None:
            budget.reset()


def clear_all_budgets() -> None:
    """Wipe all budgets. For tests and session teardown."""
    with _budgets_lock:
        _budgets.clear()


def budget_snapshot(session_key: str) -> Optional[Dict[str, float]]:
    """Snapshot a session's budget, or None when never touched."""
    with _budgets_lock:
        budget = _budgets.get(session_key)
    return budget.snapshot() if budget is not None else None
