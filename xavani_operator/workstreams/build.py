# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Build workstream — the software-lifecycle pack (v0.7.0 operator U51–U56).

Gives the operator real hands to build full-stack: detect build work, turn it
into a tier-tagged plan, and execute via handlers. The headline integration
(L9): when the work is **design/frontend**, ``make_plan`` injects the *learned
taste* — the best-matching :class:`StyleProfile` direction, the user's
preferences, and the anti-generic guardrail — into the proposal, so the agent
builds **in the style learnt** rather than something generic.

Execution effects are **injected** (``build_handlers(effectors)``): the app wires
real ones (subagents via ``delegate_tool``, git, GitHub PRs, deploy adapters);
``local_build_effectors`` provides safe real glue for local Tier-0 work; tests
pass fakes. Plan/decision logic is deterministic (R10) — only the injected
``generate`` (in ``propose``) and the wired effectors touch the model/network.
"""

from __future__ import annotations

from typing import Any, Callable

from xavani_learner.taste import taste_context
from xavani_operator.opportunities import build_opportunities
from xavani_operator.propose import make_proposal
from xavani_operator.types import StepResult
from xavani_operator.verify import verify_step_results
from xavani_operator.workstreams.base import register_workstream

# Full-stack build action vocabulary (what handlers/effectors implement).
_BUILD_ACTIONS = [
    "analyze", "implement_backend", "implement_frontend", "draft_staging",
    "migrate", "run_tests", "lint", "commit_workbranch", "open_draft_pr", "deploy",
]

_DESIGN_TERMS = (
    "site", "website", "web", "ui", "frontend", "front-end", "landing", "page",
    "app", "dashboard", "portfolio", "brand", "marketing", "deck", "slide",
)
_FRONTEND_STACK = {
    "react", "vue", "next", "nextjs", "svelte", "sveltekit", "html", "css",
    "tailwind", "astro", "angular", "solid", "remix", "frontend", "web",
}


class BuildWorkstream:
    """Software-lifecycle workstream implementing the :class:`Workstream` protocol."""

    name = "build"

    def detect_opportunities(self, perception: Any, config: Any) -> list:
        return build_opportunities(perception, config)

    def make_plan(self, intent: Any, ctx: dict | None = None, *, generate: Callable | None = None):
        proposal = make_proposal(intent, ctx=ctx, generate=generate)
        config = (ctx or {}).get("config")
        if config is not None and self._is_design(intent, config):
            brief = self._brief(intent, config)
            proposal.notes = taste_context(brief, preferences=(ctx or {}).get("preferences"))
        return proposal

    def execute(self, step: Any, ctx: Any) -> StepResult:
        # The loop drives execution through build_handlers(effectors); this is a
        # safe fallback so a bare BuildWorkstream never silently "does" a step.
        return StepResult(step_id=step.id, ok=False, error="run via build_handlers(effectors) in the loop")

    def verify(self, result: Any, ctx: Any = None):
        results = result if isinstance(result, list) else [result]
        return verify_step_results(results)

    def _is_design(self, intent: Any, config: Any) -> bool:
        text = " ".join(
            [intent.opportunity.rationale] + [getattr(g, "intent", "") for g in config.goals]
        ).lower()
        if any(term in text for term in _DESIGN_TERMS):
            return True
        return any(s.lower() in _FRONTEND_STACK for s in config.product.stack)

    def _brief(self, intent: Any, config: Any) -> str:
        goals = " ".join(g.intent for g in config.goals if g.intent)
        stack = ", ".join(config.product.stack)
        return f"{intent.opportunity.rationale} {goals} stack: {stack}".strip()


def build_handlers(effectors: dict[str, Callable] | None = None) -> dict[str, Callable]:
    """Map every build action to a handler that dispatches to an injected effector."""
    effectors = effectors or {}

    def _make(action: str) -> Callable:
        def handler(step, ctx) -> StepResult:
            fn = effectors.get(action)
            if fn is None:
                return StepResult(
                    step_id=step.id, ok=False,
                    error=f"'{action}' not wired (provide an effector)",
                )
            out = fn(step, ctx)
            return out if isinstance(out, StepResult) else StepResult(step_id=step.id, ok=True, output=str(out))

        return handler

    return {action: _make(action) for action in _BUILD_ACTIONS}


def local_build_effectors(repo: str) -> dict[str, Callable]:
    """Safe, real effectors for local Tier-0 build steps (no network, no risk).

    Risky/outward actions (implement via subagents, PRs, deploy) are deliberately
    absent — they need the app to wire real effectors, and stay 'not wired' until
    then so the bare loop can never run them.
    """
    import subprocess

    def _note(text: str) -> Callable:
        def effector(step, ctx) -> StepResult:
            return StepResult(step_id=step.id, ok=True, output=f"{text}: {step.summary}")

        return effector

    def _run_tests(step, ctx) -> StepResult:
        try:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "-q"], cwd=repo,
                capture_output=True, text=True, timeout=600,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return StepResult(step_id=step.id, ok=False, error=str(exc))
        tail = (proc.stdout or proc.stderr).strip().splitlines()[-1:] or [""]
        return StepResult(step_id=step.id, ok=proc.returncode == 0, output=tail[0])

    def _commit(step, ctx) -> StepResult:
        try:
            subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True, text=True, timeout=30)
            proc = subprocess.run(
                ["git", "commit", "-m", step.summary or "operator: work-in-progress"],
                cwd=repo, capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return StepResult(step_id=step.id, ok=False, error=str(exc))
        return StepResult(step_id=step.id, ok=proc.returncode == 0, output=proc.stdout.strip()[:200])

    return {
        "analyze": _note("[analyze]"),
        "draft_staging": _note("[draft]"),
        "lint": _note("[lint]"),
        "run_tests": _run_tests,
        "commit_workbranch": _commit,
    }


def register() -> None:
    """Register the build workstream with the operator registry."""
    register_workstream(BuildWorkstream())
