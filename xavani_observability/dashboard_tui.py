# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C03: Real-time dashboard TUI.

Curses-based dashboard showing active agents, queue depth, model
latencies, cost burn, and tool health. The data sources are the metrics
collector, the error budgets, and the cost ledger. The TUI loop is thin;
all logic lives in pure data-source functions so it is testable without
a terminal.

Usage::

    from xavani_observability.dashboard_tui import run_dashboard

    run_dashboard(refresh_sec=2.0)

The data-source contract (tested):

    snapshot = collect_snapshot(collector, budgets=None, ledger=None, queue_size=0)
    lines = render_snapshot(snapshot)
"""

from __future__ import annotations

import curses
from typing import Any, Callable, Dict, List, Optional

from xavani_observability.error_budget import ErrorBudget, get_tool_budget


def collect_snapshot(
    collector: Any,
    budgets: Optional[Dict[str, ErrorBudget]] = None,
    ledger: Optional[Any] = None,
    queue_size: int = 0,
) -> Dict[str, Any]:
    """Collect one dashboard snapshot from the observability sources.

    Args:
        collector: MetricsCollector instance.
        budgets: {subsystem: ErrorBudget} map. Defaults to the process-wide
            tools budget when None.
        ledger: CostLedger instance for cost burn. None reports 0.0.
        queue_size: Current gateway queue depth. 0 when unknown.

    Returns:
        A plain dict snapshot ready for render_snapshot.
    """
    summary = collector.get_summary()
    budgets = budgets if budgets is not None else {"tools": get_tool_budget()}
    cost_burn_usd = 0.0
    if ledger is not None:
        report = ledger.report(hours=1)
        cost_burn_usd = float(report.get("total_usd", 0.0))

    models = [
        {
            "model": name,
            "calls": int(stats.get("call_count", 0)),
            "avg_ms": float(stats.get("avg_ms", 0.0)),
            "p95_ms": float(stats.get("p95_ms", 0.0)),
        }
        for name, stats in summary.get("llms", {}).items()
    ]
    tools = []
    for name, stats in summary.get("tools", {}).items():
        error_rates = summary.get("error_rates", {})
        error_rate_pct = float(error_rates.get(name, {}).get("error_rate_pct", 0.0))
        tools.append(
            {
                "tool": name,
                "calls": int(stats.get("call_count", 0)),
                "avg_ms": float(stats.get("avg_ms", 0.0)),
                "p95_ms": float(stats.get("p95_ms", 0.0)),
                "error_rate_pct": error_rate_pct,
            }
        )
    budget_rows = []
    for subsystem, budget in budgets.items():
        availability = budget.availability()
        remaining = budget.budget_remaining()
        budget_rows.append(
            {
                "subsystem": subsystem,
                "slo": float(budget.slo),
                "availability": availability,
                "remaining": remaining,
            }
        )
    return {
        "active_agents": int(summary.get("active_sessions", 0)),
        "queue_depth": int(queue_size),
        "total_calls": int(summary.get("total_tool_calls", 0))
        + int(summary.get("total_llm_calls", 0)),
        "total_errors": int(summary.get("total_errors", 0)),
        "overall_error_rate_pct": float(summary.get("overall_error_rate", 0.0)),
        "uptime_seconds": float(summary.get("uptime_seconds", 0.0)),
        "cost_burn_usd": cost_burn_usd,
        "models": models,
        "tools": tools,
        "budgets": budget_rows,
    }


def _fmt_optional(value: Optional[float]) -> str:
    """Format an optional float as percentage, or 'n/a' when None."""
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def render_snapshot(snapshot: Dict[str, Any]) -> List[str]:
    """Render a snapshot to terminal lines. Returns the line list."""
    lines: List[str] = [
        "Xavani dashboard",
        (
            f"  active agents: {snapshot['active_agents']}  "
            f"queue: {snapshot['queue_depth']}  "
            f"uptime: {snapshot['uptime_seconds']:.0f}s"
        ),
        (
            f"  calls: {snapshot['total_calls']}  "
            f"errors: {snapshot['total_errors']} "
            f"({snapshot['overall_error_rate_pct']:.2f}%)  "
            f"cost (1h): ${snapshot['cost_burn_usd']:.4f}"
        ),
    ]
    if snapshot["models"]:
        lines.append("  models:")
        for row in snapshot["models"]:
            lines.append(
                f"    {row['model']:<32} calls={row['calls']:<5} "
                f"avg={row['avg_ms']:.0f}ms p95={row['p95_ms']:.0f}ms"
            )
    else:
        lines.append("  models: none")
    if snapshot["tools"]:
        lines.append("  tools:")
        for row in snapshot["tools"]:
            lines.append(
                f"    {row['tool']:<24} calls={row['calls']:<5} "
                f"avg={row['avg_ms']:.0f}ms p95={row['p95_ms']:.0f}ms "
                f"err={row['error_rate_pct']:.2f}%"
            )
    else:
        lines.append("  tools: none")
    lines.append("  error budgets:")
    for row in snapshot["budgets"]:
        lines.append(
            f"    {row['subsystem']:<12} slo={row['slo']:.2%} "
            f"avail={_fmt_optional(row['availability'])} "
            f"remaining={_fmt_optional(row['remaining'])}"
        )
    return lines


def run_dashboard(
    collector: Any,
    refresh_sec: float = 2.0,
    ledger: Optional[Any] = None,
    queue_size_fn: Optional[Callable[[], int]] = None,
) -> None:
    """Run the curses dashboard loop. Not unit-tested (needs a tty)."""

    def _draw(stdscr: Any) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        while True:
            queue_size = queue_size_fn() if queue_size_fn is not None else 0
            snapshot = collect_snapshot(
                collector, ledger=ledger, queue_size=queue_size
            )
            lines = render_snapshot(snapshot)
            stdscr.erase()
            for index, line in enumerate(lines[: stdscr.getmaxyx()[0] - 1]):
                stdscr.addstr(index, 0, line[: stdscr.getmaxyx()[1] - 1])
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord("q"), ord("Q"), 27):
                return
            curses.napms(int(refresh_sec * 1000))

    curses.wrapper(_draw)
