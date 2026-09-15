# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Behavior tests for the host-side verification runner."""

import os

import pytest

from agent.completion_contract import CheckReceipt, CompletionContract
from agent.verification_runner import (
    current_revision,
    make_backend_execute,
    note_work_change,
    run_host_check,
    run_required_checks,
    set_completion_contract,
    store_for,
)


def make_contract(**changes):
    values = dict(
        contract_id="contract-1",
        session_id="session-1",
        workspace_id="workspace-1",
        workflow_id="engineering",
        goal="Pass the checks.",
        required_checks=("unit", "lint"),
        required_skills=(),
        allowed_actions=(),
        approved_at="2026-01-01T00:00:00Z",
        revision="r1",
    )
    values.update(changes)
    return CompletionContract(**values)


class _StubAgent:
    def __init__(self):
        self._completion_contract = None
        self._verification_check_commands = {}
        self._verification_execute = None
        self._verification_store = None
        self._verification_repair_attempts = 0
        self._verification_revision_serial = 0
        self._verification_last_decision = None
        self.session_id = "session-1"


def _record(_result):
    def execute(argv, cwd):
        _result["argv"] = argv
        _result["cwd"] = cwd
        return {"exit_code": 0}
    return execute


def test_run_host_check_maps_exit_codes():
    contract = make_contract()
    execute = _record({})
    passed = run_host_check(contract, "unit", ("pytest",), "cwd", "r1:0", execute)
    assert passed.status == "passed" and passed.exit_code == 0
    assert passed.origin == "host" and passed.command_argv == ("pytest",)

    def fail_execute(argv, cwd):
        return {"exit_code": 1}
    failed = run_host_check(contract, "unit", ("pytest",), "cwd", "r1:0", fail_execute)
    assert failed.status == "failed" and failed.exit_code == 1


@pytest.mark.parametrize("result,expected", [
    ({"cancelled": True}, "cancelled"),
    ({"blocked": True}, "blocked"),
    ({"exit_code": None}, "blocked"),
    ({"exit_code": "0"}, "blocked"),
])
def test_run_host_check_maps_special_results(result, expected):
    def execute(argv, cwd):
        return result
    receipt = run_host_check(make_contract(), "unit", ("pytest",), "cwd", "r1:0", execute)
    assert receipt.status == expected and receipt.exit_code is None


@pytest.mark.parametrize("exc", [OSError("boom"), TimeoutError("slow")])
def test_run_host_check_blocks_on_transport_failures(exc):
    def execute(argv, cwd):
        raise exc
    receipt = run_host_check(make_contract(), "unit", ("pytest",), "cwd", "r1:0", execute)
    assert receipt.status == "blocked" and receipt.exit_code is None


def test_run_host_check_validates_inputs():
    contract = make_contract()
    execute = _record({})
    with pytest.raises(ValueError):
        run_host_check(contract, "other", ("pytest",), "cwd", "r1:0", execute)
    with pytest.raises(ValueError):
        run_host_check(contract, "unit", ["pytest"], "cwd", "r1:0", execute)
    with pytest.raises(ValueError):
        run_host_check(contract, "unit", (), "cwd", "r1:0", execute)
    with pytest.raises(ValueError):
        run_host_check(contract, "unit", ("pytest", ""), "cwd", "r1:0", execute)


def test_set_contract_validates_and_resets():
    agent = _StubAgent()
    agent._verification_revision_serial = 9
    agent._verification_repair_attempts = 2
    contract = make_contract()
    with pytest.raises(ValueError):
        set_completion_contract(agent, contract, {"unit": ("pytest",)})
    with pytest.raises(ValueError):
        set_completion_contract(agent, contract, {"unit": ("pytest",), "lint": ("ruff",), "extra": ("x",)})
    with pytest.raises(ValueError):
        set_completion_contract(agent, contract, {"unit": ["pytest"], "lint": ("ruff",)})
    with pytest.raises(ValueError):
        set_completion_contract(agent, "not-a-contract", {})
    set_completion_contract(agent, contract, {"unit": ("pytest",), "lint": ("ruff",)})
    assert agent._verification_revision_serial == 0
    assert agent._verification_repair_attempts == 0
    assert agent._verification_last_decision is None


def test_revision_serial_and_note_work_change():
    agent = _StubAgent()
    with pytest.raises(ValueError):
        current_revision(agent)
    note_work_change(agent)
    assert agent._verification_revision_serial == 0
    set_completion_contract(agent, make_contract(), {"unit": ("pytest",), "lint": ("ruff",)})
    assert current_revision(agent) == "r1:0"
    note_work_change(agent)
    assert current_revision(agent) == "r1:1"


def test_store_for_caches_one_store():
    agent = _StubAgent()
    assert store_for(agent) is store_for(agent)


def test_run_required_checks_appends_receipts_in_contract_order():
    agent = _StubAgent()
    calls = []

    def execute(argv, cwd):
        calls.append(argv)
        return {"exit_code": 0}
    set_completion_contract(agent, make_contract(), {"lint": ("ruff",), "unit": ("pytest",)}, execute=execute)
    receipts = run_required_checks(agent, "task-1")
    assert [r.check_id for r in receipts] == ["unit", "lint"]
    assert calls == [("pytest",), ("ruff",)]
    stored = store_for(agent).for_contract("contract-1")
    assert stored == receipts
    assert all(r.revision == "r1:0" for r in stored)


def test_run_required_checks_uses_current_revision_after_change():
    agent = _StubAgent()
    def execute(argv, cwd):
        return {"exit_code": 0}
    set_completion_contract(agent, make_contract(), {"unit": ("pytest",), "lint": ("ruff",)}, execute=execute)
    run_required_checks(agent, "task-1")
    note_work_change(agent)
    run_required_checks(agent, "task-1")
    stored = store_for(agent).for_contract("contract-1")
    assert {r.revision for r in stored} == {"r1:0", "r1:1"}


def test_default_execute_resolves_backend(monkeypatch):
    agent = _StubAgent()

    class _Backend:
        def execute(self, command, cwd=""):
            return {"returncode": 2}
    import tools.terminal_tool as terminal_tool
    monkeypatch.setattr(terminal_tool, "get_active_env", lambda task_id: _Backend())
    set_completion_contract(agent, make_contract(), {"unit": ("pytest",), "lint": ("ruff",)})
    receipts = run_required_checks(agent, "task-1")
    assert [r.status for r in receipts] == ["failed", "failed"]


def test_default_execute_blocks_without_backend(monkeypatch):
    agent = _StubAgent()
    import tools.terminal_tool as terminal_tool
    monkeypatch.setattr(terminal_tool, "get_active_env", lambda task_id: None)
    set_completion_contract(agent, make_contract(), {"unit": ("pytest",), "lint": ("ruff",)})
    receipts = run_required_checks(agent, "task-1")
    assert [r.status for r in receipts] == ["blocked", "blocked"]
