# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Host-side runner for completion-contract checks.

The runner executes only the check commands approved in the active
contract, records one host receipt per check, and lets the agent loop
decide completion from current evidence.  A model response never
creates a receipt.
"""

from __future__ import annotations

import shlex
from datetime import datetime, timezone
from uuid import uuid4

from agent.completion_contract import CheckReceipt, CompletionContract
from agent.verification_receipts import ReceiptStore
from xavani_constants import get_xavani_home

_RECEIPT_DB_NAME = "verification_receipts.db"
_DEFAULT_CWD_LABEL = "<backend-default>"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_host_check(
    contract: CompletionContract,
    check_id: str,
    command_argv: tuple[str, ...],
    cwd: str,
    revision: str,
    execute,
    artifact_hashes: tuple[tuple[str, str], ...] = (),
) -> CheckReceipt:
    """Execute one approved check and record what the host observed."""
    if not isinstance(contract, CompletionContract):
        raise ValueError("contract shall be a CompletionContract.")
    if check_id not in contract.required_checks:
        raise ValueError("The contract does not require this check.")
    if not isinstance(command_argv, tuple) or not command_argv:
        raise ValueError("The check command shall be a nonempty tuple.")
    if any(not isinstance(arg, str) or not arg for arg in command_argv):
        raise ValueError("The check command shall contain nonempty text.")
    started = _now()
    exit_code = None
    try:
        result = execute(command_argv, cwd)
        if not isinstance(result, dict):
            status = "blocked"
        elif result.get("cancelled"):
            status = "cancelled"
        elif result.get("blocked"):
            status = "blocked"
        elif type(result.get("exit_code")) is not int:
            status = "blocked"
        else:
            exit_code = result["exit_code"]
            status = "passed" if exit_code == 0 else "failed"
    except (OSError, TimeoutError):
        status = "blocked"
    return CheckReceipt(
        receipt_id=uuid4().hex,
        contract_id=contract.contract_id,
        check_id=check_id,
        workspace_id=contract.workspace_id,
        revision=revision,
        command_argv=command_argv,
        cwd=cwd or _DEFAULT_CWD_LABEL,
        exit_code=exit_code,
        status=status,
        artifact_hashes=artifact_hashes,
        started_at=started,
        finished_at=_now(),
        origin="host",
    )


def make_backend_execute(task_id: str):
    """Build an execute callable from the active terminal backend.

    The backend resolves the working directory itself, so the runner's
    cwd is a receipt label only.  Failures degrade to blocked.
    """
    def execute(command_argv: tuple[str, ...], cwd: str) -> dict:
        try:
            from tools.terminal_tool import get_active_env

            backend = get_active_env(task_id)
        except Exception:
            return {"blocked": True}
        if backend is None:
            return {"blocked": True}
        try:
            result = backend.execute(shlex.join(command_argv))
        except Exception:
            return {"blocked": True}
        if not isinstance(result, dict):
            return {"blocked": True}
        return {"exit_code": result.get("returncode")}
    return execute


def set_completion_contract(agent, contract, check_commands, execute=None) -> CompletionContract:
    """Attach an approved contract and its exact check commands to an agent."""
    if not isinstance(contract, CompletionContract):
        raise ValueError("contract shall be a CompletionContract.")
    if not isinstance(check_commands, dict) or set(check_commands) != set(contract.required_checks):
        raise ValueError("check_commands shall match the required checks.")
    normalized = {}
    for check_id, argv in check_commands.items():
        if not isinstance(argv, tuple) or not argv or any(
            not isinstance(arg, str) or not arg for arg in argv
        ):
            raise ValueError("Each check requires a nonempty command tuple.")
        normalized[check_id] = tuple(argv)
    agent._completion_contract = contract
    agent._verification_check_commands = normalized
    agent._verification_execute = execute
    agent._verification_repair_attempts = 0
    agent._verification_revision_serial = 0
    agent._verification_last_decision = None
    return contract


def current_revision(agent) -> str:
    contract = getattr(agent, "_completion_contract", None)
    if contract is None:
        raise ValueError("No active completion contract.")
    return f"{contract.revision}:{int(getattr(agent, '_verification_revision_serial', 0))}"


def note_work_change(agent) -> None:
    """Invalidate current receipts after a work-product change."""
    if getattr(agent, "_completion_contract", None) is None:
        return
    agent._verification_revision_serial = int(
        getattr(agent, "_verification_revision_serial", 0)
    ) + 1


def store_for(agent) -> ReceiptStore:
    store = getattr(agent, "_verification_store", None)
    if store is None:
        store = ReceiptStore(get_xavani_home() / _RECEIPT_DB_NAME)
        agent._verification_store = store
    return store


def run_required_checks(agent, task_id: str | None = None) -> tuple[CheckReceipt, ...]:
    """Run every required check and append its receipt."""
    contract = getattr(agent, "_completion_contract", None)
    if contract is None:
        raise ValueError("No active completion contract.")
    execute = getattr(agent, "_verification_execute", None)
    if execute is None:
        execute = make_backend_execute(task_id or getattr(agent, "session_id", "") or "default")
    revision = current_revision(agent)
    store = store_for(agent)
    commands = agent._verification_check_commands
    receipts = []
    for check_id in contract.required_checks:
        receipt = run_host_check(contract, check_id, commands[check_id], "", revision, execute)
        store.append(receipt)
        receipts.append(receipt)
    return tuple(receipts)
