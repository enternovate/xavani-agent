# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Report: summarise a cycle for the user (v0.7.0 operator U43/U44).

Builds a :class:`CycleReport` from what was proposed/executed/verified, renders
it human-readably, and delivers it via an injected ``sender`` (CLI prints it; the
loop can route it to the user's channel). Pure and import-light (no LLM).
"""

from __future__ import annotations

from typing import Callable

from xavani_operator.types import CycleReport, Proposal, StepResult, Verdict


def build_cycle_report(
    cycle_id: str,
    proposal: Proposal,
    results: list[StepResult],
    verdict: Verdict,
) -> CycleReport:
    """Summarise one cycle's outcome into a :class:`CycleReport`."""
    executed = sum(1 for r in results if r.ok)
    opp = proposal.intent.opportunity
    notes = (
        f"{opp.workstream}/{opp.kind}: {executed}/{len(proposal.steps)} steps ran; "
        f"verify {'ok' if verdict.ok else 'FAILED'}"
    )
    if not verdict.ok and verdict.findings:
        notes += f" — {verdict.findings[0]}"
    return CycleReport(
        cycle_id=cycle_id,
        proposed=1,
        approved=1,
        executed=executed,
        verified=1 if verdict.ok else 0,
        notes=notes,
    )


def render_report(report: CycleReport) -> str:
    """Render a :class:`CycleReport` as a short, human-readable block."""
    return "\n".join([
        f"Cycle {report.cycle_id}",
        f"  proposed {report.proposed} · approved {report.approved} · "
        f"executed {report.executed} · verified {report.verified}",
        f"  {report.notes}",
    ])


def deliver_report(report: CycleReport, sender: Callable[[str], object] | None = None) -> bool:
    """Deliver the rendered report via ``sender``; return whether it was sent."""
    text = render_report(report)
    if sender is None:
        return False
    sender(text)
    return True
