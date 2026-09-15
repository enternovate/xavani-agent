# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Behavior tests for the pure completion contract."""

from dataclasses import replace

import pytest

from agent.completion_contract import (
    CheckReceipt,
    CompletionContract,
    CompletionDecision,
    decide_completion,
)


def make_contract(**changes):
    values = dict(
        contract_id="contract-1",
        session_id="session-1",
        workspace_id="workspace-1",
        workflow_id="engineering",
        goal="Pass the required checks.",
        required_checks=("unit", "lint"),
        required_skills=(),
        allowed_actions=(),
        approved_at="2026-01-01T00:00:00Z",
        revision="r1",
    )
    values.update(changes)
    return CompletionContract(**values)


def make_receipt(**changes):
    values = dict(
        receipt_id="receipt-1",
        contract_id="contract-1",
        check_id="unit",
        workspace_id="workspace-1",
        revision="r1",
        command_argv=("python3", "-m", "pytest"),
        cwd="/workspace",
        exit_code=0,
        status="passed",
        artifact_hashes=(),
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        origin="host",
    )
    values.update(changes)
    return CheckReceipt(**values)


def passing_pair():
    return (
        make_receipt(),
        make_receipt(receipt_id="receipt-2", check_id="lint"),
    )


class TestDecision:
    def test_current_host_evidence_passes(self):
        assert decide_completion(make_contract(), passing_pair(), "r1") == CompletionDecision("passed")

    def test_missing_evidence_is_unverified(self):
        assert decide_completion(make_contract(), (), "r1") == CompletionDecision(
            "unverified", missing_checks=("unit", "lint")
        )

    def test_partial_evidence_lists_only_missing(self):
        decision = decide_completion(make_contract(), (make_receipt(),), "r1")
        assert decision == CompletionDecision("unverified", missing_checks=("lint",))

    def test_stale_revision_is_unverified(self):
        receipts = (
            make_receipt(revision="r0"),
            make_receipt(receipt_id="receipt-2", check_id="lint", revision="r0"),
        )
        decision = decide_completion(make_contract(), receipts, "r1")
        assert decision == CompletionDecision("unverified", missing_checks=("unit", "lint"))

    def test_model_receipt_is_ignored(self):
        receipts = tuple(replace(r, origin="model") for r in passing_pair())
        decision = decide_completion(make_contract(), receipts, "r1")
        assert decision == CompletionDecision("unverified", missing_checks=("unit", "lint"))

    def test_foreign_contract_and_workspace_are_ignored(self):
        receipts = tuple(
            replace(r, contract_id="other") for r in passing_pair()
        ) + tuple(replace(r, workspace_id="other-ws") for r in passing_pair())
        decision = decide_completion(make_contract(), receipts, "r1")
        assert decision == CompletionDecision("unverified", missing_checks=("unit", "lint"))

    def test_unknown_check_id_is_ignored(self):
        receipt = make_receipt(check_id="other", receipt_id="receipt-x")
        decision = decide_completion(make_contract(), (receipt,), "r1")
        assert decision == CompletionDecision("unverified", missing_checks=("unit", "lint"))

    def test_failed_check_fails_even_with_other_pass(self):
        receipts = (
            make_receipt(),
            make_receipt(receipt_id="receipt-2", check_id="lint", status="failed", exit_code=1),
        )
        decision = decide_completion(make_contract(), receipts, "r1")
        assert decision == CompletionDecision("failed", missing_checks=(), failed_checks=("lint",))

    def test_later_failure_replaces_earlier_pass(self):
        receipts = (
            make_receipt(),
            make_receipt(receipt_id="receipt-2", status="failed", exit_code=1),
            make_receipt(receipt_id="receipt-3", check_id="lint"),
        )
        decision = decide_completion(make_contract(), receipts, "r1")
        assert decision.state == "failed"
        assert decision.failed_checks == ("unit",)

    def test_later_pass_replaces_earlier_failure(self):
        receipts = (
            make_receipt(status="failed", exit_code=1),
            make_receipt(receipt_id="receipt-2"),
            make_receipt(receipt_id="receipt-3", check_id="lint"),
        )
        assert decide_completion(make_contract(), receipts, "r1") == CompletionDecision("passed")

    def test_blocked_and_cancelled_checks_report_blocked(self):
        receipts = (
            make_receipt(status="blocked", exit_code=None),
            make_receipt(receipt_id="receipt-2", check_id="lint", status="cancelled", exit_code=None),
        )
        decision = decide_completion(make_contract(), receipts, "r1")
        assert decision == CompletionDecision("blocked", failed_checks=("unit", "lint"))

    def test_result_order_follows_contract_not_insertion(self):
        contract = make_contract(required_checks=("alpha", "beta", "gamma"))
        receipts = (
            make_receipt(check_id="gamma", status="failed", exit_code=1),
            make_receipt(receipt_id="receipt-2", check_id="beta", status="failed", exit_code=1),
        )
        decision = decide_completion(contract, receipts, "r1")
        assert decision.failed_checks == ("beta", "gamma")
        assert decision.missing_checks == ("alpha",)

    def test_explicit_read_only_contract_needs_no_checks(self):
        contract = make_contract(required_checks=(), read_only=True)
        assert decide_completion(contract, (), "r1") == CompletionDecision("not_required")


class TestContractValidation:
    def test_work_contract_requires_a_check(self):
        with pytest.raises(ValueError):
            make_contract(required_checks=())

    @pytest.mark.parametrize("field", ["contract_id", "session_id", "workspace_id", "workflow_id", "goal", "approved_at", "revision"])
    def test_identifiers_require_nonempty_text(self, field):
        with pytest.raises(ValueError):
            make_contract(**{field: " "})

    def test_duplicate_checks_are_rejected(self):
        with pytest.raises(ValueError):
            make_contract(required_checks=("unit", "unit"))

    @pytest.mark.parametrize("field", ["required_checks", "required_skills", "allowed_actions"])
    def test_containers_must_be_tuples(self, field):
        with pytest.raises(ValueError):
            make_contract(**{field: ["unit"]})

    def test_check_entries_must_be_nonempty_text(self):
        with pytest.raises(ValueError):
            make_contract(required_checks=("",))

    def test_read_only_must_be_a_bool(self):
        with pytest.raises(ValueError):
            make_contract(read_only="yes")


class TestReceiptValidation:
    def test_invalid_status_is_rejected(self):
        with pytest.raises(ValueError):
            make_receipt(status="maybe")

    def test_passed_requires_exact_zero_exit_code(self):
        with pytest.raises(ValueError):
            make_receipt(exit_code=1)
        with pytest.raises(ValueError):
            make_receipt(exit_code=None)

    def test_exit_code_rejects_bool(self):
        with pytest.raises(ValueError):
            make_receipt(exit_code=True)

    def test_non_passing_status_allows_none_exit_code(self):
        assert make_receipt(status="blocked", exit_code=None).exit_code is None

    @pytest.mark.parametrize("value", [(("only-one",),), (("", "hash"),), (("name", ""),)])
    def test_artifact_hash_pairs_require_two_nonempty_strings(self, value):
        with pytest.raises(ValueError):
            make_receipt(artifact_hashes=value)

    @pytest.mark.parametrize("field", ["receipt_id", "contract_id", "check_id", "workspace_id", "revision", "cwd", "started_at", "finished_at", "origin"])
    def test_receipt_text_fields_require_nonempty_values(self, field):
        with pytest.raises(ValueError):
            make_receipt(**{field: ""})

    def test_command_argv_must_be_a_tuple_of_text(self):
        with pytest.raises(ValueError):
            make_receipt(command_argv=["pytest"])
        with pytest.raises(ValueError):
            make_receipt(command_argv=("pytest", ""))


class TestDecisionInputValidation:
    def test_current_revision_must_be_nonempty_text(self):
        with pytest.raises(ValueError):
            decide_completion(make_contract(), (), "")

    def test_receipts_must_be_a_tuple(self):
        with pytest.raises(ValueError):
            decide_completion(make_contract(), [make_receipt()], "r1")
