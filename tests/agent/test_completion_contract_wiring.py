# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Loop wiring tests for the completion contract (R1 Task 05a).

Drives the REAL agent loop with a scripted faux provider.  A host
attaches an approved contract with check commands; the loop runs the
checks through the injected execute callable and may not finish as
verified until current host receipts pass.
"""

from unittest.mock import patch

import pytest

from run_agent import AIAgent
from tests.harness.faux_provider import ScriptedSession

from agent.completion_contract import CompletionContract


def _make_tool_defs(*names: str) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": f"{n} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for n in names
    ]


@pytest.fixture()
def make_agent():
    _openai_patch = patch("run_agent.OpenAI", new=object())
    _openai_patch.start()

    def _with_provider(session: ScriptedSession, tools=("skills_list",)):
        nonlocal _openai_patch
        factory = session.client_factory()
        _openai_patch.stop()
        _openai_patch = patch("run_agent.OpenAI", factory)
        _openai_patch.start()
        with (
            patch("run_agent.get_tool_definitions", return_value=_make_tool_defs(*tools)),
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
        return agent

    yield _with_provider
    try:
        _openai_patch.stop()
    except Exception:
        pass


def make_contract(**changes):
    values = dict(
        contract_id="contract-1",
        session_id="session-1",
        workspace_id="workspace-1",
        workflow_id="engineering",
        goal="Pass the required checks.",
        required_checks=("unit",),
        required_skills=(),
        allowed_actions=(),
        approved_at="2026-01-01T00:00:00Z",
        revision="r1",
    )
    values.update(changes)
    return CompletionContract(**values)


def attach_contract(agent, execute, checks=(("unit", ("pytest",)),)):
    from agent.verification_runner import set_completion_contract

    contract = make_contract(required_checks=tuple(c for c, _ in checks))
    set_completion_contract(agent, contract, {c: argv for c, argv in checks}, execute=execute)
    return contract


_NUDGE_MARKER = "[System: verification is not complete"


def nudge_count(messages):
    """Count repair nudges by content; the loop may merge them into a user row."""
    return sum(
        m["content"].count(_NUDGE_MARKER)
        for m in messages
        if isinstance(m.get("content"), str)
    )


def test_passing_checks_finalize_verified(make_agent):
    session = ScriptedSession()
    session.text("done")
    agent = make_agent(session)
    calls = []

    def execute(argv, cwd):
        calls.append(argv)
        return {"exit_code": 0}

    attach_contract(agent, execute)
    result = agent.run_conversation("finish the task")

    assert result["verification_state"] == "passed"
    assert result["missing_checks"] == []
    assert result["failed_checks"] == []
    assert calls == [("pytest",)]
    assert len(session.provider.calls) == 1
    assert nudge_count(result["messages"]) == 0


def test_failed_check_triggers_one_repair_then_passes(make_agent):
    session = ScriptedSession()
    session.text("done")
    session.text("fixed")
    agent = make_agent(session)
    state = {"calls": 0}

    def execute(argv, cwd):
        state["calls"] += 1
        return {"exit_code": 1 if state["calls"] == 1 else 0}

    attach_contract(agent, execute)
    result = agent.run_conversation("finish the task")

    assert result["verification_state"] == "passed"
    assert agent._verification_repair_attempts == 1
    assert len(session.provider.calls) == 2
    assert nudge_count(result["messages"]) == 1


def test_exhausted_repairs_finish_unverified(make_agent):
    session = ScriptedSession()
    session.text("done")
    session.text("still broken")
    session.text("sorry")
    agent = make_agent(session)

    def execute(argv, cwd):
        return {"exit_code": 1}

    attach_contract(agent, execute)
    result = agent.run_conversation("finish the task")

    assert result["verification_state"] == "failed"
    assert agent._verification_repair_attempts == 2
    assert len(session.provider.calls) == 3
    assert nudge_count(result["messages"]) == 2


def test_cancelled_check_blocks_without_repairs(make_agent):
    session = ScriptedSession()
    session.text("done")
    agent = make_agent(session)

    def execute(argv, cwd):
        return {"cancelled": True}

    attach_contract(agent, execute)
    result = agent.run_conversation("finish the task")

    assert result["verification_state"] == "blocked"
    assert agent._verification_repair_attempts == 0
    assert len(session.provider.calls) == 1
    assert nudge_count(result["messages"]) == 0


def test_without_contract_turn_is_not_required(make_agent):
    session = ScriptedSession()
    session.text("plain answer")
    agent = make_agent(session)

    result = agent.run_conversation("just chat")

    assert result["verification_state"] == "not_required"
    assert result["missing_checks"] == []
    assert result["failed_checks"] == []
    assert len(session.provider.calls) == 1


def test_plugin_transform_cannot_upgrade_failed_state(make_agent):
    session = ScriptedSession()
    session.text("done")
    session.text("still broken")
    session.text("sorry")
    agent = make_agent(session)

    def execute(argv, cwd):
        return {"exit_code": 1}

    def fake_hook(name, **kwargs):
        return ["TRANSFORMED"] if name == "transform_llm_output" else []

    attach_contract(agent, execute)
    with patch("xavani_cli.plugins.invoke_hook", fake_hook):
        result = agent.run_conversation("finish the task")

    assert result["verification_state"] == "failed"
    assert result["final_response"] == "TRANSFORMED"
