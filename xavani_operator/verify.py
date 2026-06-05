# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Verify: post-conditions for a cycle (v0.7.0 operator U40/U41).

After ``act`` runs an approved plan, verify decides whether it actually worked:
all steps succeeded, checks (tests/lint/smoke) pass, and any outward content
respects the brand policy. Verification is **deterministic** (R10) — checks are
injected callables (the loop wires real test/lint runners; tests pass fakes), and
content policy is a pure rule scan. A failing :class:`Verdict` is what triggers
rollback in the loop.
"""

from __future__ import annotations

from typing import Any, Callable

from xavani_operator.types import StepResult, Verdict


def verify_step_results(results: list[StepResult]) -> Verdict:
    """A Verdict over the executor's results: ok iff every step succeeded."""
    fails = [r for r in results if not r.ok]
    if fails:
        return Verdict.fail("; ".join(r.error or f"step {r.step_id} failed" for r in fails))
    return Verdict.ok_()


def run_checks(checks: list[Callable[[Any], Any]], ctx: Any = None) -> Verdict:
    """Run injected checks (each → ``Verdict`` or ``(ok, message)``) and aggregate."""
    findings: list[str] = []
    warnings: list[str] = []
    for check in checks:
        result = check(ctx)
        if isinstance(result, Verdict):
            if not result.ok:
                findings.extend(result.findings)
            warnings.extend(result.warnings)
        else:
            ok, message = result
            if not ok:
                findings.append(message)
    return Verdict(ok=not findings, findings=findings, warnings=warnings)


def check_content_policy(text: str, config) -> Verdict:
    """Deterministic brand/policy gate for outward content (no LLM)."""
    low = text.lower()
    bad = [d for d in config.brand.donts if d and d.lower() in low]
    if bad:
        return Verdict.fail(f"content violates brand donts: {', '.join(bad)}")
    return Verdict.ok_()
