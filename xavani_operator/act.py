# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Plan executor / dispatcher (v0.7.0 operator U37/U39).

Runs an **approved** proposal by dispatching each :class:`PlanStep` to a handler
keyed on its ``action_class``. Handlers are **injected** (the loop wires real
ones over the agent's tools/subagents in M3+; tests pass fakes) — so this module
is pure dispatch with no hardcoded side effects or model client (R10).

Tier discipline at execution:
* Tier 3 (BLOCK) steps **re-confirm** via the injected ``reconfirm`` callback,
  even though the plan was approved (force-push, prod data ops, payments).
* Execution **stops at the first failure** (missing handler, raised exception, or
  a handler returning ``ok=False``) so a broken plan never charges ahead.
"""

from __future__ import annotations

from typing import Any, Callable

from xavani_operator.types import PlanStep, Proposal, StepResult, Tier

Handler = Callable[[PlanStep, Any], Any]


def execute_plan(
    proposal: Proposal,
    handlers: dict[str, Handler],
    ctx: Any = None,
    reconfirm: Callable[[PlanStep], bool] | None = None,
) -> list[StepResult]:
    """Execute ``proposal`` step by step; return the results (stops on first failure)."""
    results: list[StepResult] = []
    for step in proposal.steps:
        if step.tier == Tier.BLOCK:
            if reconfirm is None or not reconfirm(step):
                results.append(StepResult(
                    step_id=step.id, ok=False,
                    error="declined (tier-3 step not re-confirmed)",
                ))
                break
        handler = handlers.get(step.action_class)
        if handler is None:
            results.append(StepResult(
                step_id=step.id, ok=False,
                error=f"no handler for action '{step.action_class}'",
            ))
            break
        try:
            out = handler(step, ctx)
        except Exception as exc:  # a handler blew up — stop the plan
            results.append(StepResult(step_id=step.id, ok=False, error=str(exc)))
            break
        result = out if isinstance(out, StepResult) else StepResult(
            step_id=step.id, ok=True, output=str(out)
        )
        results.append(result)
        if not result.ok:
            break
    return results
