# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R2 Task 19 — action reconciliation (Code Pack O).

Microcycles: reconciliation reads the exact external target; an ``unknown``
outcome blocks retries until resolution; an unconfigured connector returns
``Unavailable`` without burning the approval.
"""

from __future__ import annotations

import pytest

from xavani_operator.approval_queue import ActionRequest, ApprovalQueue
from xavani_operator.state import OperatorState

NOW = 1000.0


def _request(**overrides) -> ActionRequest:
    base = dict(
        profile="default",
        workspace_id="ws-finance",
        operation="send_invoice",
        target="vendor:acme@example.com",
        payload={
            "recipient": "acme@example.com",
            "amount_minor": 125000,
            "attachment_sha256": "aaa111",
        },
    )
    base.update(overrides)
    return ActionRequest(**base)


class FakeConnector:
    """Echoes the received digest on read; counts every call."""

    def __init__(self, configured=True, received=True):
        self.configured = configured
        self.received = received
        self.submits = []
        self.reads = []

    def submit(self, record):
        self.submits.append(record.id)
        return {"accepted": True}

    def read_target(self, target, record):
        self.reads.append(target)
        if self.received:
            return {"action_digest": record.digest}
        return {"action_digest": "something-else"}


class SlowConnector(FakeConnector):
    def submit(self, record):
        import time as _t
        _t.sleep(0.3)
        return super().submit(record)


def _bound(queue: ApprovalQueue, request=None, *, aid="a1"):
    request = request or _request()
    queue.enqueue_action_for(request, approval_id=aid)
    queue.request_approval(aid)
    return queue.approve_action(aid, now=NOW)


# --- 8: reconciliation reads the exact external target -----------------------

def test_reconciliation_reads_the_exact_target_and_verifies(tmp_path):
    from xavani_operator.act import execute_action, reconcile_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    connector = FakeConnector()
    execute_action(queue, "a1", connector, request=_request(), now=NOW + 5)
    outcome = reconcile_action(queue, "a1", connector, now=NOW + 6)
    assert connector.reads == ["vendor:acme@example.com"]  # the exact target
    assert outcome.ok is True
    assert outcome.state == "verified"
    assert queue.get_action("a1").state == "verified"


def test_reconciliation_mismatch_is_failed(tmp_path):
    from xavani_operator.act import execute_action, reconcile_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    connector = FakeConnector(received=False)
    execute_action(queue, "a1", connector, request=_request(), now=NOW + 5)
    outcome = reconcile_action(queue, "a1", connector, now=NOW + 6)
    assert outcome.ok is False
    assert outcome.state == "failed"
    assert queue.get_action("a1").state == "failed"


# --- 9: unknown blocks retries until resolution ------------------------------

def test_unknown_blocks_retries_until_resolved(tmp_path):
    from xavani_operator.act import execute_action, reconcile_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue, aid="a1")
    unknown = execute_action(
        queue, "a1", SlowConnector(), request=_request(), now=NOW + 5, submit_timeout_s=0.05,
    )
    assert unknown.state == "unknown"

    # A fresh approval for the same action cannot execute while unresolved.
    _bound(queue, aid="a2")
    blocked = execute_action(queue, "a2", FakeConnector(), request=_request(), now=NOW + 6)
    assert blocked.ok is False
    assert "unknown" in blocked.error.lower()

    # Resolution of a1's unknown unblocks the path; a2 was untouched.
    resolved = reconcile_action(queue, "a1", FakeConnector(), now=NOW + 7)
    assert resolved.state == "verified"
    assert queue.get_action("a1").state == "verified"
    run = execute_action(queue, "a2", FakeConnector(), request=_request(), now=NOW + 8)
    assert run.ok is True


def test_reconcile_refuses_non_executing_states(tmp_path):
    from xavani_operator.act import reconcile_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    queue.enqueue_action_for(_request(), approval_id="a1")
    outcome = reconcile_action(queue, "a1", FakeConnector(), now=NOW + 5)
    assert outcome.ok is False
    assert "executing" in outcome.error.lower()


# --- 10: unconfigured connector -> Unavailable, approval untouched -----------

def test_unconfigured_connector_returns_unavailable(tmp_path):
    from xavani_operator.act import execute_action

    for connector in (None, FakeConnector(configured=False)):
        queue = ApprovalQueue(OperatorState(root=tmp_path / str(connector)))
        _bound(queue)
        outcome = execute_action(queue, "a1", connector, request=_request(), now=NOW + 5)
        assert outcome.ok is False
        assert outcome.unavailable is True
        assert "unavailable" in outcome.error.lower()
        record = queue.get_action("a1")
        assert record.consumed is False
        assert record.state == "approved"  # the approval is still usable
