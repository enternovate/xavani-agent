# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R2 Task 19 — approvals bound to exact actions (Code Pack O).

Microcycles: a changed recipient, amount, attachment, or profile invalidates
an approval; an expired approval cannot execute; a duplicate submit cannot
execute twice; a timeout after submit enters ``unknown``; a failed action
never restores a consumed approval. The transition table gates every move.
"""

from __future__ import annotations

import pytest

from xavani_operator.approval_queue import (
    ACTION_TRANSITIONS,
    APPROVAL_TTL_SECONDS,
    ActionRequest,
    ApprovalQueue,
    action_can_execute,
    action_digest,
    transition_action,
)
from xavani_operator.audit import AuditLog
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


def _bound(queue: ApprovalQueue, request: ActionRequest | None = None, *, aid="a1"):
    request = request or _request()
    approval = queue.enqueue_action_for(request, approval_id=aid)
    queue.request_approval(aid)
    return queue.approve_action(aid, now=NOW)


class FakeConnector:
    """Records every call; echoes the digest it received back on read."""

    def __init__(self, configured=True, fail=None, received=True):
        self.configured = configured
        self.fail = fail
        self.received = received
        self.submits = []
        self.reads = []

    def submit(self, record):
        self.submits.append(record.id)
        if self.fail == "raise":
            raise ConnectionError("link down")
        return {"accepted": True}

    def read_target(self, target, record):
        self.reads.append(target)
        if self.received:
            return {"action_digest": record.digest}
        return {"action_digest": "something-else"}


# --- canonical digest --------------------------------------------------------

def test_action_digest_is_stable_and_covers_the_identity():
    req = _request()
    assert req.digest() == action_digest(
        profile=req.profile, workspace_id=req.workspace_id,
        operation=req.operation, target=req.target, payload=req.payload,
    )
    assert _request().digest() == req.digest()  # stable across instances
    assert _request(payload={**req.payload, "recipient": "x@example.com"}).digest() != req.digest()
    with pytest.raises(ValueError):
        action_digest(profile="", workspace_id="w", operation="op", target="t", payload={})


# --- 1-4: changed context invalidates the approval ---------------------------

@pytest.mark.parametrize(
    "field,value",
    [
        ("recipient", "evil@example.com"),
        ("amount_minor", 999999999),
        ("attachment_sha256", "bbb222"),
    ],
)
def test_changed_payload_invalidates(tmp_path, field, value):
    from xavani_operator.act import execute_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    altered = _request(payload={**_request().payload, field: value})
    outcome = execute_action(queue, "a1", FakeConnector(), request=altered, now=NOW + 10)
    assert outcome.ok is False
    assert outcome.state != "executing"
    assert "changed" in outcome.error.lower()
    # The refusal did not consume the approval: the exact action still runs.
    outcome = execute_action(queue, "a1", FakeConnector(), request=_request(), now=NOW + 11)
    assert outcome.ok is True


def test_changed_profile_invalidates(tmp_path):
    from xavani_operator.act import execute_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    altered = _request(profile="other-profile")
    outcome = execute_action(queue, "a1", FakeConnector(), request=altered, now=NOW + 10)
    assert outcome.ok is False
    assert "changed" in outcome.error.lower()


# --- 5: expiry ---------------------------------------------------------------

def test_expired_approval_cannot_execute(tmp_path):
    from xavani_operator.act import execute_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    later = NOW + APPROVAL_TTL_SECONDS + 1
    outcome = execute_action(queue, "a1", FakeConnector(), request=_request(), now=later)
    assert outcome.ok is False
    assert outcome.state == "expired"
    record = queue.get_action("a1")
    assert record.state == "expired"
    assert record.consumed is False


# --- 6: one attempt only -----------------------------------------------------

def test_duplicate_submit_cannot_execute_twice(tmp_path):
    from xavani_operator.act import execute_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    connector = FakeConnector()
    first = execute_action(queue, "a1", connector, request=_request(), now=NOW + 5)
    assert first.ok is True
    second = execute_action(queue, "a1", connector, request=_request(), now=NOW + 6)
    assert second.ok is False
    assert "consum" in second.error.lower()
    assert connector.submits == ["a1"]
    assert queue.get_action("a1").attempts == 1


# --- 7: timeout after submit -> unknown; failures never restore consumed -----

def test_timeout_after_submit_enters_unknown(tmp_path):
    from xavani_operator.act import execute_action

    class SlowConnector(FakeConnector):
        def submit(self, record):
            import time as _t
            _t.sleep(0.3)
            return super().submit(record)

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    outcome = execute_action(
        queue, "a1", SlowConnector(), request=_request(), now=NOW + 5, submit_timeout_s=0.05,
    )
    assert outcome.ok is False
    assert outcome.state == "unknown"
    record = queue.get_action("a1")
    assert record.consumed is True  # the attempt may have reached the outside


def test_failed_action_does_not_restore_a_consumed_approval(tmp_path):
    from xavani_operator.act import execute_action

    queue = ApprovalQueue(OperatorState(root=tmp_path))
    _bound(queue)
    outcome = execute_action(queue, "a1", FakeConnector(fail="raise"), request=_request(), now=NOW + 5)
    assert outcome.ok is False
    assert outcome.state == "failed"
    record = queue.get_action("a1")
    assert record.consumed is True
    retry = execute_action(queue, "a1", FakeConnector(), request=_request(), now=NOW + 6)
    assert retry.ok is False  # a retry needs a fresh approval


# --- the transition table ----------------------------------------------------

def test_transition_table_is_exhaustive():
    assert ACTION_TRANSITIONS["draft"] == ("pending_approval",)
    assert ACTION_TRANSITIONS["pending_approval"] == ("approved", "denied", "expired")
    assert ACTION_TRANSITIONS["approved"] == ("executing", "expired")  # expiry can pass while approved
    assert ACTION_TRANSITIONS["executing"] == ("verified", "failed", "unknown")
    assert ACTION_TRANSITIONS["unknown"] == ("verified", "failed")


def test_unknown_cannot_transition_back_to_executing():
    with pytest.raises(ValueError):
        transition_action("unknown", "executing")
    with pytest.raises(ValueError):
        transition_action("pending_approval", "executing")
    assert transition_action("approved", "executing") == "executing"


def test_only_approved_may_execute():
    assert action_can_execute("approved") is True
    for state in ("draft", "pending_approval", "denied", "expired", "executing", "verified", "failed", "unknown"):
        assert action_can_execute(state) is False


# --- audit chain -------------------------------------------------------------

def test_lifecycle_writes_tamper_evident_audit(tmp_path):
    from xavani_operator.act import execute_action

    st = OperatorState(root=tmp_path)
    audit = AuditLog(st)
    queue = ApprovalQueue(st, audit=audit)
    _bound(queue)
    execute_action(queue, "a1", FakeConnector(), request=_request(), now=NOW + 5)
    assert audit.verify() is True
    events = [e["event"] for e in st.list("audit")]
    kinds = {e.get("type") for e in events}
    assert {"action-propose", "action-request", "action-approve", "action-consume"} <= kinds
    digests = {e.get("digest") for e in events}
    assert len(digests) == 1 and next(iter(digests))
