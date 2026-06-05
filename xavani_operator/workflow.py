# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Durable workflow / DAG engine (v0.7.0 operator U79/U80/U84).

A small dependency-ordered step runner with **retries** and **idempotent
resume**: each completed step is recorded in the state store keyed by an
idempotency key, so re-running a workflow after a crash skips what already
succeeded and only does what's left. The operator models long, multi-step jobs
(a build-and-ship, a multi-channel campaign) as workflows so an interruption
never repeats a side effect (no duplicate posts, PRs, or payments-requested).

Pure orchestration — step functions are injected; this module makes **no LLM
calls** (R10). Ordering is deterministic (topological, ties broken by id).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

_COLLECTION = "workflow"


@dataclass
class WorkflowStep:
    """One node of a workflow DAG."""

    id: str
    run: Callable[[dict], Any]
    deps: list[str] = field(default_factory=list)
    idempotency_key: str = ""


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "step"


class Workflow:
    """A durable, dependency-ordered workflow."""

    def __init__(self, steps: list[WorkflowStep], store: Any = None, name: str = "wf") -> None:
        self.steps = {s.id: s for s in steps}
        self.store = store
        self.name = name

    def _record_key(self, step: WorkflowStep) -> str:
        return _safe(f"{self.name}.{step.idempotency_key or step.id}")

    def _topo(self) -> list[str]:
        """Deterministic topological order (ties broken by id); raise on a cycle."""
        indeg = {sid: 0 for sid in self.steps}
        for step in self.steps.values():
            for dep in step.deps:
                if dep not in self.steps:
                    raise ValueError(f"unknown dependency '{dep}' for step '{step.id}'")
                indeg[step.id] += 1
        queue = sorted(sid for sid, d in indeg.items() if d == 0)
        order: list[str] = []
        while queue:
            sid = queue.pop(0)
            order.append(sid)
            for step in self.steps.values():
                if sid in step.deps:
                    indeg[step.id] -= 1
                    if indeg[step.id] == 0:
                        queue.append(step.id)
                        queue.sort()
        if len(order) != len(self.steps):
            raise ValueError("workflow has a cycle")
        return order

    def run(self, ctx: dict | None = None, max_retries: int = 1) -> dict[str, dict]:
        """Run the workflow; return {step_id: {status, ...}}. Resumes from the store."""
        ctx = ctx if ctx is not None else {}
        results: dict[str, dict] = {}
        for sid in self._topo():
            step = self.steps[sid]

            if self.store is not None and self.store.get(_COLLECTION, self._record_key(step)):
                results[sid] = {"status": "skipped"}
                continue

            if any(results.get(d, {}).get("status") in ("failed", "blocked") for d in step.deps):
                results[sid] = {"status": "blocked"}
                continue

            attempt, ok, output, error = 0, False, None, ""
            while attempt <= max_retries:
                try:
                    output = step.run(ctx)
                    ok = True
                    break
                except Exception as exc:
                    error = str(exc)
                    attempt += 1

            if ok:
                results[sid] = {"status": "done", "output": output}
                if self.store is not None:
                    self.store.put(_COLLECTION, self._record_key(step), {"step": sid, "done": True})
            else:
                results[sid] = {"status": "failed", "error": error}
        return results
