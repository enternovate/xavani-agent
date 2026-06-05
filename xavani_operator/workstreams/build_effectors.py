# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Real build effectors — the M4 last mile (v0.7.0 operator U53/U54/U58/U59).

Production effectors the operator wires into ``build_handlers`` so the build
workstream produces **real artifacts**:

* ``staged_implementation_effector`` — implement via an injected ``code_agent``
  (the app wires ``delegate_tool`` / an LLM coding loop). With none, it writes a
  precise, **taste-infused implementation brief** (a real file) for a subagent or
  human to pick up — so the operator always produces a concrete deliverable.
* ``gh_pr_effector`` — a real **GitHub draft PR** via ``gh`` (push + ``gh pr
  create --draft``).
* ``deploy_effector`` — runs a **configurable deploy command** (Vercel/Docker/SSH
  — whatever the product defines).

Every shell/network call goes through an injectable ``run`` so this is unit-tested
with fakes (no real PRs/deploys in tests) while being real by default. These are
the *only* parts that touch network — decision/planning stays deterministic (R10).
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable

from xavani_operator.types import StepResult
from xavani_operator.workstreams.build import local_build_effectors

_BRIEF_FILE = "OPERATOR_IMPLEMENTATION_BRIEF.md"


def _default_run(cmd: list[str], repo: str):
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=600)


def _build_brief(step: Any, ctx: Any) -> str:
    taste = ""
    if isinstance(ctx, dict):
        taste = ctx.get("taste") or ""
    return (
        f"# Operator implementation brief\n\n"
        f"**Task:** {step.summary}\n"
        f"**Action:** {step.action_class}\n\n"
        f"Implement this on the current work branch. **Follow the approved design "
        f"direction (the learned taste) in the proposal** — stay creative, never "
        f"produce generic/template-y output.\n\n"
        f"{taste}\n"
    )


def staged_implementation_effector(repo: str, code_agent: Callable[[str], Any] | None = None) -> Callable:
    """Implement via an injected ``code_agent``; else stage a real brief artifact."""

    def effector(step, ctx) -> StepResult:
        brief = _build_brief(step, ctx)
        if code_agent is not None:
            result = code_agent(brief)
            return StepResult(step_id=step.id, ok=True, output=str(result)[:200])
        path = Path(repo) / _BRIEF_FILE
        try:
            path.write_text(brief, encoding="utf-8")
        except OSError as exc:
            return StepResult(step_id=step.id, ok=False, error=str(exc))
        return StepResult(step_id=step.id, ok=True, output=f"staged implementation brief at {path.name}")

    return effector


def gh_pr_effector(repo: str, base: str = "main", run: Callable | None = None) -> Callable:
    """Open a real GitHub **draft** PR for the current branch via ``gh``."""
    run = run or _default_run

    def effector(step, ctx) -> StepResult:
        push = run(["git", "push", "-u", "origin", "HEAD"], repo)
        if push.returncode != 0:
            return StepResult(step_id=step.id, ok=False, error=f"push failed: {push.stderr.strip()[:160]}")
        pr = run(["gh", "pr", "create", "--draft", "--fill", "--base", base], repo)
        if pr.returncode != 0:
            return StepResult(step_id=step.id, ok=False, error=f"gh pr create failed: {pr.stderr.strip()[:160]}")
        return StepResult(step_id=step.id, ok=True, output=pr.stdout.strip()[:200])

    return effector


def deploy_effector(command: str, repo: str, run: Callable | None = None) -> Callable:
    """Run a configurable deploy command (Vercel/Docker/SSH/…)."""
    run = run or _default_run

    def effector(step, ctx) -> StepResult:
        if not command.strip():
            return StepResult(step_id=step.id, ok=False, error="no deploy command configured")
        proc = run(shlex.split(command), repo)
        if proc.returncode != 0:
            return StepResult(step_id=step.id, ok=False, error=f"deploy failed: {proc.stderr.strip()[:160]}")
        return StepResult(step_id=step.id, ok=True, output=proc.stdout.strip()[:200])

    return effector


def tool_build_effectors(
    repo: str,
    *,
    code_agent: Callable[[str], Any] | None = None,
    deploy_command: str = "",
    base: str = "main",
    run: Callable | None = None,
) -> dict[str, Callable]:
    """Assemble the full real effector set for the build workstream."""
    effectors = dict(local_build_effectors(repo))
    effectors["implement_backend"] = staged_implementation_effector(repo, code_agent=code_agent)
    effectors["implement_frontend"] = staged_implementation_effector(repo, code_agent=code_agent)
    effectors["open_draft_pr"] = gh_pr_effector(repo, base=base, run=run)
    effectors["deploy"] = deploy_effector(deploy_command, repo, run=run)
    return effectors
