# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Learn: record outcomes and adjust opportunity weights (v0.7.0 operator U45/U46).

After a cycle, the operator remembers what happened and gets a little smarter:
successful kinds of work gain weight, failing ones lose it. Weights are a
**deterministic** multiplier the opportunity engine can later apply to scores
(closing the feedback loop without an LLM, R10). Outcomes also persist as cycle
records so ``perceive`` can read the last cycle. Builds on the operator state
store; richer episodic learning hooks into ``xavani_memory`` later.
"""

from __future__ import annotations

import re

from xavani_operator.types import CycleReport

_WEIGHT_MIN = 0.1
_WEIGHT_MAX = 2.0


def _key(kind: str) -> str:
    """Sanitise an opportunity kind into a safe state key."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", kind) or "unknown"


def get_weight(state, kind: str, default: float = 1.0) -> float:
    """Recall the learned weight for ``kind`` (1.0 if never seen)."""
    d = state.get("weights", _key(kind))
    return float(d["weight"]) if d else default


def update_weight(state, kind: str, success: bool, step: float = 0.1) -> float:
    """Nudge a kind's weight up (success) or down (failure); persist and return it."""
    current = get_weight(state, kind)
    new = current + step if success else current - step
    new = round(max(_WEIGHT_MIN, min(_WEIGHT_MAX, new)), 4)
    state.put("weights", _key(kind), {"kind": kind, "weight": new})
    return new


def record_outcome(state, report: CycleReport, kind: str, success: bool) -> None:
    """Persist a cycle outcome and update the kind's learned weight."""
    state.put("cycles", report.cycle_id, {
        "cycle_id": report.cycle_id,
        "created_at": report.created_at,
        "executed": report.executed,
        "verified": report.verified,
        "kind": kind,
        "success": bool(success),
    })
    update_weight(state, kind, success)
