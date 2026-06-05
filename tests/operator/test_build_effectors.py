# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for real build effectors (v0.7.0 operator U53/U54/U58/U59)."""

from __future__ import annotations

from xavani_operator.types import PlanStep, Tier
from xavani_operator.workstreams.build_effectors import (
    deploy_effector,
    gh_pr_effector,
    staged_implementation_effector,
    tool_build_effectors,
)


class _FakeProc:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _step(action_class="implement_backend"):
    return PlanStep(id="s", action_class=action_class, tier=Tier.AUTO, summary="build the API")


# --- U53/U54: implement (code-agent seam, real artifact default) -----------

def test_staged_implementation_writes_a_real_brief(tmp_path):
    result = staged_implementation_effector(str(tmp_path))(_step(), {"config": None})
    assert result.ok is True
    assert (tmp_path / "OPERATOR_IMPLEMENTATION_BRIEF.md").exists()


def test_staged_implementation_uses_injected_code_agent(tmp_path):
    seen = {}

    def agent(brief):
        seen["brief"] = brief
        return "implemented"

    result = staged_implementation_effector(str(tmp_path), code_agent=agent)(_step(), {})
    assert result.ok is True
    assert "implemented" in result.output
    assert "build the API" in seen["brief"]


# --- U58: real GitHub draft PR (via gh, injectable runner) -----------------

def test_gh_pr_effector_creates_draft_pr():
    cmds = []

    def run(cmd, repo):
        cmds.append(cmd[:3])
        return _FakeProc(0, out="https://github.com/x/y/pull/1")

    result = gh_pr_effector(".", run=run)(_step("open_draft_pr"), None)
    assert result.ok is True
    assert "pull/1" in result.output


def test_gh_pr_effector_reports_push_failure():
    def run(cmd, repo):
        return _FakeProc(1, err="no upstream") if cmd[:2] == ["git", "push"] else _FakeProc(0)

    result = gh_pr_effector(".", run=run)(_step("open_draft_pr"), None)
    assert result.ok is False
    assert "push" in result.error.lower()


# --- U59: deploy (configurable command, injectable runner) -----------------

def test_deploy_effector_runs_command():
    def run(cmd, repo):
        return _FakeProc(0, out="deployed ok")

    result = deploy_effector("vercel deploy", ".", run=run)(_step("deploy"), None)
    assert result.ok is True
    assert "deployed" in result.output


def test_deploy_effector_without_command_is_unconfigured():
    result = deploy_effector("", ".")(_step("deploy"), None)
    assert result.ok is False
    assert "no deploy" in result.error.lower()


# --- assembly ---------------------------------------------------------------

def test_tool_build_effectors_assemble_full_stack():
    eff = tool_build_effectors(".", deploy_command="echo x")
    for action in [
        "analyze", "run_tests", "commit_workbranch",
        "implement_backend", "implement_frontend", "open_draft_pr", "deploy",
    ]:
        assert action in eff
