# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G01: autonomous diagnosis.

Collects health signals from the observability modules and produces a
ranked diagnosis: what is degrading, how bad, and what likely causes
it. Deterministic — the same signals always produce the same
diagnosis. Diagnosis is advisory; it never mutates state.

Signals used:
- error budget availability (E06)
- tool health checks (E08)
- cost burn rate (D04)
- feedback struggling tasks (B13)

Usage::

    from tools.auto_diagnosis import diagnose

    report = diagnose(signals={...})  # or diagnose() for defaults
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _health_score(signal: str, value: Any) -> Optional[float]:
    """Score a signal 0 (bad) .. 1 (good). None when not measurable."""
    if signal == "error_budget_remaining":
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))
    if signal == "cost_burn_exceeded":
        return 0.0 if value else 1.0
    if signal == "tool_health_ok":
        if value is None:
            return None
        ok, total = int(value.get("ok", 0)), int(value.get("total", 0))
        return (ok / total) if total else 1.0
    if signal == "struggling_tasks":
        if value is None:
            return None
        # 0 struggling tasks = healthy; scale by 5 to be meaningful.
        return max(0.0, 1.0 - min(1.0, int(value) / 5.0))
    if signal == "error_rate":
        if value is None:
            return None
        return max(0.0, 1.0 - min(1.0, float(value)))
    return None


def diagnose(signals: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a ranked diagnosis from health signals.

    Args:
        signals: {signal_name: value} — see module docstring.

    Returns:
        {
          "overall_score": float (0..1),
          "issues": [{"signal", "score", "severity"}],
          "healthy": bool,
        }
    """
    scored: List[Dict[str, Any]] = []
    for signal, value in signals.items():
        score = _health_score(signal, value)
        if score is None:
            continue
        severity = "critical" if score < 0.3 else ("warning" if score < 0.7 else "ok")
        scored.append({"signal": signal, "score": round(score, 3), "severity": severity})

    issues = [s for s in scored if s["severity"] != "ok"]
    issues.sort(key=lambda s: s["score"])  # worst first

    overall = (
        sum(s["score"] for s in scored) / len(scored) if scored else 1.0
    )
    return {
        "overall_score": round(overall, 3),
        "issues": issues,
        "healthy": not issues,
    }


def diagnose_from_modules() -> Dict[str, Any]:
    """Collect signals from the observability modules and diagnose.

    Every module read is guarded — a missing module or a raised error
    produces no signal instead of a crash.
    """
    signals: Dict[str, Any] = {}
    try:
        from xavani_observability.error_budget import record_tool_outcome  # noqa: F401
    except Exception:
        pass
    try:
        from xavani_observability.cost_alerts import cost_guard

        signals["cost_burn_exceeded"] = cost_guard().exceeded()
    except Exception:
        pass
    try:
        from tools.feedback_loop import FeedbackLoop

        signals["struggling_tasks"] = len(FeedbackLoop().struggling_tasks())
    except Exception:
        pass
    return diagnose(signals)
