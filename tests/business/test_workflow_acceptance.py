# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R2 Task 20 — business workflow acceptance (36 cases, scripted provider).

Every case runs its script through the REAL agent loop with the scripted
provider (tests.harness.faux_provider): real tool dispatch executes the
write_file calls, so the artifacts on disk come from the real harness, and
each case's checks assert objective file facts (existence, content,
absence) — never a phrase like "invoice complete".

The ``unapproved`` cases then exercise the real approval gate (Task 19):
the drafted consequential action must NOT execute without an approval, and
the same action WITH an approval must execute — the refusal is the gate,
not broken plumbing.

This proves harness behavior only. Task 25 measures real-model behavior.
No network and no API keys are used.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from xavani_operator.act import execute_action
from xavani_operator.approval_queue import ActionRequest, ApprovalQueue
from xavani_operator.state import OperatorState

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "business" / "workflows.json"


def _load_workflows() -> list[dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data["workflows"]


WORKFLOWS = _load_workflows()
ALL_CASES = [
    (workflow, case) for workflow in WORKFLOWS for case in workflow["cases"]
]

_WRITE_FILE_DEF = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
}


def _materialise(value, workspace: Path):
    """Replace the @ws placeholder with the temporary workspace path."""
    if isinstance(value, str):
        return value.replace("@ws/", str(workspace) + "/")
    if isinstance(value, dict):
        return {k: _materialise(v, workspace) for k, v in value.items()}
    if isinstance(value, list):
        return [_materialise(v, workspace) for v in value]
    return value


def _run_case_script(case: dict, workspace: Path) -> dict:
    """Run the case's scripted turns through the real loop."""
    from run_agent import AIAgent
    from tests.harness.faux_provider import ScriptedSession

    session = ScriptedSession()
    for step in case["script"]:
        kind, payload = step[0], _materialise(step[1], workspace)
        if kind == "write_file":
            session.tool_call("write_file", payload)
        elif kind == "text":
            session.text(payload)
        else:  # pragma: no cover - fixture authoring error
            raise ValueError(f"unknown script step: {kind}")

    factory = session.client_factory()
    with (
        patch("run_agent.OpenAI", factory),
        patch("run_agent.get_tool_definitions", return_value=[_WRITE_FILE_DEF]),
        patch("run_agent.check_toolset_requirements", return_value={}),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent._persist_session = lambda *a, **k: None
        agent._save_trajectory = lambda *a, **k: None
        agent._save_session_log = lambda *a, **k: None
        agent.suppress_status_output = True
        result = agent.run_conversation(case["prompt"])
    return result


def _seed_sources(workflow: dict, case: dict, workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    sources = case.get("sources", workflow["sources"])
    for name, content in sources.items():
        target = workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _assert_checks(case: dict, workspace: Path) -> None:
    for check in case["checks"]:
        target = workspace / check["path"]
        if check.get("exists") is True:
            assert target.is_file(), f"{case['id']}: expected artifact {check['path']}"
            text = target.read_text(encoding="utf-8")
            for needle in check.get("contains", []):
                assert needle in text, f"{case['id']}: {check['path']} is missing {needle!r}"
        elif check.get("exists") is False:
            assert not target.exists(), f"{case['id']}: {check['path']} must not exist"


class _Connector:
    """A working connector that records execution outside the workspace."""

    configured = True

    def __init__(self, marker: Path) -> None:
        self.marker = marker

    def submit(self, record):
        self.marker.write_text(record.digest, encoding="utf-8")
        return {"accepted": True}


def _assert_unapproved_gate(case: dict, workflow: dict, workspace: Path, tmp_path: Path) -> None:
    """The drafted action must not execute without an approval — the real gate."""
    proposal_check = next(c for c in case["checks"] if c.get("exists") is True)
    side_effect_check = next(c for c in case["checks"] if c.get("exists") is False)
    proposal = json.loads((workspace / proposal_check["path"]).read_text(encoding="utf-8"))

    request = ActionRequest(
        profile="business-harness",
        workspace_id=f"{workflow['id']}-harness",
        operation=proposal["operation"],
        target=proposal["target"],
        payload=proposal.get("payload", {}),
    )
    queue = ApprovalQueue(OperatorState(root=tmp_path / "operator"))
    queue.enqueue_action_for(request, approval_id="case-action")  # drafted only

    marker = tmp_path / "control" / "executed.marker"
    marker.parent.mkdir(parents=True, exist_ok=True)
    connector = _Connector(marker)

    refused = execute_action(queue, "case-action", connector, request=request)
    assert refused.ok is False, f"{case['id']}: ran without approval"
    assert "not executable" in refused.error, f"{case['id']}: unexpected refusal: {refused.error}"
    assert not marker.exists(), f"{case['id']}: the connector ran without approval"
    assert not (workspace / side_effect_check["path"]).exists()

    # Control: the same action WITH an approval executes — the refusal was
    # the approval gate, not broken plumbing. The record walks the legal
    # path: draft -> pending_approval -> approved.
    queue.request_approval("case-action")
    queue.approve_action("case-action", now=time.time())
    allowed = execute_action(queue, "case-action", connector, request=request)
    assert allowed.ok is True, f"{case['id']}: approved action did not execute"


def _run_case(workflow: dict, case: dict, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _seed_sources(workflow, case, workspace)
    result = _run_case_script(case, workspace)
    assert result.get("completed") is True, f"{case['id']}: the scripted run did not complete"
    _assert_checks(case, workspace)
    if case["kind"] == "unapproved":
        _assert_unapproved_gate(case, workflow, workspace, tmp_path)


# ── coverage guards ─────────────────────────────────────────────────────────


def test_fixture_covers_every_workflow_with_three_cases():
    assert [w["id"] for w in WORKFLOWS] == [f"B{i:02d}" for i in range(1, 13)]
    for workflow in WORKFLOWS:
        kinds = [c["kind"] for c in workflow["cases"]]
        assert kinds == ["valid", "missing", "unapproved"], workflow["id"]
    assert len(ALL_CASES) == 36


# ── the 36 cases ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("workflow", "case"),
    ALL_CASES,
    ids=[case["id"] for _, case in ALL_CASES],
)
def test_workflow_case(workflow, case, tmp_path):
    _run_case(workflow, case, tmp_path)


# ── per-workflow aggregate nodes (bench verifier targets) ───────────────────


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=[w["id"] for w in WORKFLOWS])
def test_workflow_all_cases(workflow, tmp_path):
    for index, case in enumerate(workflow["cases"]):
        _run_case(workflow, case, tmp_path / f"case-{index}")
