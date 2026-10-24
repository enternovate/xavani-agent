# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Pure completion contract: current host evidence decides pass or block.

Only host-origin receipts that match the live contract, workspace, and
revision can satisfy a required check.  A model response never creates a
receipt, so a confident answer alone cannot mark work verified.
"""

from dataclasses import dataclass
from typing import Literal, Tuple

ReceiptStatus = Literal["passed", "failed", "blocked", "cancelled"]
VerificationState = Literal["not_required", "unverified", "passed", "failed", "blocked"]

_RECEIPT_STATUSES = frozenset({"passed", "failed", "blocked", "cancelled"})


def _require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} shall contain nonempty text.")


def _require_text_tuple(value: object, label: str) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{label} shall be a tuple.")
    for entry in value:
        _require_text(entry, label)


@dataclass(frozen=True)
class CompletionContract:
    contract_id: str
    session_id: str
    workspace_id: str
    workflow_id: str
    goal: str
    required_checks: Tuple[str, ...]
    required_skills: Tuple[str, ...]
    allowed_actions: Tuple[str, ...]
    approved_at: str
    revision: str
    read_only: bool = False

    def __post_init__(self) -> None:
        for label in (
            "contract_id",
            "session_id",
            "workspace_id",
            "workflow_id",
            "goal",
            "approved_at",
            "revision",
        ):
            _require_text(getattr(self, label), label)
        _require_text_tuple(self.required_checks, "required_checks")
        _require_text_tuple(self.required_skills, "required_skills")
        _require_text_tuple(self.allowed_actions, "allowed_actions")
        if len(set(self.required_checks)) != len(self.required_checks):
            raise ValueError("required_checks shall not contain duplicates.")
        if type(self.read_only) is not bool:
            raise ValueError("read_only shall be a bool.")
        if not self.read_only and not self.required_checks:
            raise ValueError("A work contract shall require at least one check.")


@dataclass(frozen=True)
class CheckReceipt:
    receipt_id: str
    contract_id: str
    check_id: str
    workspace_id: str
    revision: str
    command_argv: Tuple[str, ...]
    cwd: str
    exit_code: int | None
    status: ReceiptStatus
    artifact_hashes: Tuple[Tuple[str, str], ...]
    started_at: str
    finished_at: str
    origin: str

    def __post_init__(self) -> None:
        for label in (
            "receipt_id",
            "contract_id",
            "check_id",
            "workspace_id",
            "revision",
            "cwd",
            "started_at",
            "finished_at",
            "origin",
        ):
            _require_text(getattr(self, label), label)
        if self.status not in _RECEIPT_STATUSES:
            raise ValueError("status is invalid.")
        if type(self.exit_code) is bool or (
            self.exit_code is not None and type(self.exit_code) is not int
        ):
            raise ValueError("exit_code shall be an integer or None.")
        if self.status == "passed" and self.exit_code != 0:
            raise ValueError("A passing receipt shall have exit code 0.")
        _require_text_tuple(self.command_argv, "command_argv")
        if not isinstance(self.artifact_hashes, tuple):
            raise ValueError("artifact_hashes shall be a tuple.")
        for pair in self.artifact_hashes:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("Each artifact hash shall contain a name and a hash.")
            _require_text(pair[0], "artifact name")
            _require_text(pair[1], "artifact hash")


@dataclass(frozen=True)
class CompletionDecision:
    state: VerificationState
    missing_checks: Tuple[str, ...] = ()
    failed_checks: Tuple[str, ...] = ()


def decide_completion(
    contract: CompletionContract,
    receipts: Tuple[CheckReceipt, ...],
    current_revision: str,
) -> CompletionDecision:
    """Decide the verification state from current host receipts.

    Receipts arrive in append order; the latest matching receipt for a
    check wins.  Stale revisions, foreign contracts or workspaces, model
    origins, and unknown check IDs never contribute evidence.
    """
    if not isinstance(contract, CompletionContract):
        raise ValueError("contract shall be a CompletionContract.")
    _require_text(current_revision, "current_revision")
    if not isinstance(receipts, tuple):
        raise ValueError("receipts shall be a tuple.")
    if contract.read_only and not contract.required_checks:
        return CompletionDecision("not_required")

    latest = {}
    for receipt in receipts:
        if not isinstance(receipt, CheckReceipt):
            raise ValueError("receipts shall contain CheckReceipt values.")
        if receipt.origin != "host":
            continue
        if receipt.contract_id != contract.contract_id:
            continue
        if receipt.workspace_id != contract.workspace_id:
            continue
        if receipt.revision != current_revision:
            continue
        if receipt.check_id not in contract.required_checks:
            continue
        latest[receipt.check_id] = receipt

    failed = tuple(
        check
        for check in contract.required_checks
        if check in latest and latest[check].status == "failed"
    )
    blocked = tuple(
        check
        for check in contract.required_checks
        if check in latest and latest[check].status in {"blocked", "cancelled"}
    )
    missing = tuple(check for check in contract.required_checks if check not in latest)
    if failed:
        return CompletionDecision("failed", missing_checks=missing, failed_checks=failed)
    if blocked:
        return CompletionDecision("blocked", missing_checks=missing, failed_checks=blocked)
    if missing:
        return CompletionDecision("unverified", missing_checks=missing)
    return CompletionDecision("passed")
