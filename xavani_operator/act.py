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

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from xavani_operator.approval_queue import ActionRequest, ApprovalQueue, BoundApproval
from xavani_operator.types import PlanStep, Proposal, StepResult, Tier

Handler = Callable[[PlanStep, Any], Any]


@dataclass
class ActionOutcome:
    """The result of one exact-action attempt or reconciliation."""

    ok: bool
    state: str
    error: str = ""
    output: str = ""
    unavailable: bool = False


def _connector_unavailable(connector: Any) -> bool:
    """True when no usable connector is configured for the action."""
    return connector is None or not bool(getattr(connector, "configured", True))


def _submit_with_timeout(connector: Any, record: BoundApproval, timeout_s: float) -> Any:
    """Submit with a hard deadline; a timeout leaves the outcome unknown."""
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(connector.submit, record)
    try:
        return future.result(timeout=timeout_s)
    finally:
        pool.shutdown(wait=False)


def execute_action(
    queue: ApprovalQueue,
    approval_id: str,
    connector: Any,
    *,
    request: ActionRequest | None = None,
    now: float | None = None,
    submit_timeout_s: float = 30.0,
) -> ActionOutcome:
    """Execute exactly one approved action attempt (Code Pack O discipline).

    Order of guards: known connector, unresolved-unknown retry block,
    atomic consume (digest + expiry + single attempt), then dispatch.
    """
    record = queue.get_action(approval_id)
    if record is None:
        return ActionOutcome(ok=False, state="missing", error="unknown approval")
    if _connector_unavailable(connector):
        return ActionOutcome(
            ok=False, state=record.state, unavailable=True,
            error="Unavailable: no connector is configured for this action",
        )
    if request is not None and record.state == "approved":
        guard = queue.unresolved_unknown(request)
        if guard is not None:
            return ActionOutcome(
                ok=False, state=record.state,
                error=f"blocked: unresolved unknown outcome ({guard.id})",
            )
    consumed, reason = queue.consume_action(approval_id, request=request, now=now)
    if reason:
        state = consumed.state if consumed is not None else "missing"
        return ActionOutcome(ok=False, state=state, error=reason)
    assert consumed is not None  # a successful consume always returns the record
    try:
        receipt = _submit_with_timeout(connector, consumed, submit_timeout_s)
    except TimeoutError:
        queue.resolve_action(approval_id, "unknown", note="submit timed out")
        return ActionOutcome(ok=False, state="unknown", error="submit timed out; outcome unknown")
    except Exception as exc:  # the attempt failed; the approval stays consumed
        queue.resolve_action(approval_id, "failed", note=str(exc))
        return ActionOutcome(ok=False, state="failed", error=str(exc))
    return ActionOutcome(ok=True, state=consumed.state, output=str(receipt or ""))


def reconcile_action(
    queue: ApprovalQueue,
    approval_id: str,
    connector: Any,
    *,
    now: float | None = None,
) -> ActionOutcome:
    """Resolve an executing/unknown action by reading the exact target."""
    record = queue.get_action(approval_id)
    if record is None:
        return ActionOutcome(ok=False, state="missing", error="unknown approval")
    if record.state not in ("executing", "unknown"):
        return ActionOutcome(
            ok=False, state=record.state,
            error=f"cannot reconcile: only executing or unknown actions reconcile (state: {record.state})",
        )
    if _connector_unavailable(connector):
        return ActionOutcome(
            ok=False, state=record.state, unavailable=True,
            error="Unavailable: no connector is configured for this action",
        )
    try:
        read = connector.read_target(record.request.get("target"), record) or {}
    except Exception as exc:  # noqa: BLE001 - report, never mask
        return ActionOutcome(ok=False, state=record.state, error=f"reconciliation read failed: {exc}")
    matched = read.get("action_digest") == record.digest
    outcome = "verified" if matched else "failed"
    queue.resolve_action(approval_id, outcome, note="reconciled against the external target")
    return ActionOutcome(ok=matched, state=outcome, output=str(read))


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
