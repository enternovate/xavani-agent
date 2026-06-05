# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the approval queue, tiered gate, and audit log (v0.7.0 operator U25–U27/U31/U32/U34)."""

from __future__ import annotations

from xavani_operator.approval_queue import (
    ApprovalQueue,
    authorized_steps,
    gate,
    needs_approval,
    reconfirm_steps,
    veto_window_elapsed,
)
from xavani_operator.audit import AuditLog
from xavani_operator.propose import make_proposal
from xavani_operator.state import OperatorState
from xavani_operator.types import Intent, Opportunity, ProposalStatus


def _proposal(action_classes, pid="p1"):
    def gen(intent, ctx):
        return [{"action_class": ac, "summary": ac} for ac in action_classes]

    intent = Intent(opportunity=Opportunity(id="o", kind="k", workstream="build", score=1.0))
    return make_proposal(intent, proposal_id=pid, generate=gen)


# --- U25: queue persistence -------------------------------------------------

def test_enqueue_and_get(tmp_path):
    q = ApprovalQueue(OperatorState(root=tmp_path))
    q.enqueue(_proposal(["analyze"]))
    assert q.get("p1").id == "p1"


def test_list_filters_by_status(tmp_path):
    q = ApprovalQueue(OperatorState(root=tmp_path))
    q.enqueue(_proposal(["analyze"], "p1"))
    q.enqueue(_proposal(["post_external"], "p2"))
    q.approve("p1")
    assert [p.id for p in q.list(status=ProposalStatus.APPROVED)] == ["p1"]
    assert [p.id for p in q.list(status=ProposalStatus.PENDING)] == ["p2"]


def test_approve_and_reject(tmp_path):
    q = ApprovalQueue(OperatorState(root=tmp_path))
    q.enqueue(_proposal(["post_external"], "p1"))
    assert q.approve("p1").status == ProposalStatus.APPROVED
    q.enqueue(_proposal(["post_external"], "p2"))
    assert q.reject("p2").status == ProposalStatus.REJECTED


# --- U26/U34: tiered gate (full tier matrix) -------------------------------

def test_gate_auto_approves_safe_plan():
    assert gate(_proposal(["analyze", "open_draft_pr"])) == ProposalStatus.APPROVED


def test_gate_pends_when_approval_needed_and_no_approver():
    assert gate(_proposal(["post_external"])) == ProposalStatus.PENDING


def test_gate_approver_decides():
    assert gate(_proposal(["post_external"]), approver=lambda p: True) == ProposalStatus.APPROVED
    assert gate(_proposal(["post_external"]), approver=lambda p: False) == ProposalStatus.REJECTED


def test_needs_approval_by_tier():
    assert needs_approval(_proposal(["post_external"])) is True
    assert needs_approval(_proposal(["force_push"])) is True
    assert needs_approval(_proposal(["analyze", "open_draft_pr"])) is False


# --- U27: plan-level semantics ---------------------------------------------

def test_authorized_excludes_block_reconfirm_only_block():
    p = _proposal(["analyze", "post_external", "force_push"])
    auth = {s.action_class for s in authorized_steps(p)}
    recon = {s.action_class for s in reconfirm_steps(p)}
    assert {"analyze", "post_external"} <= auth
    assert "force_push" not in auth
    assert recon == {"force_push"}


# --- U32: veto window -------------------------------------------------------

def test_veto_window_elapsed():
    assert veto_window_elapsed(100.0, 0, now=100.0) is True       # no window -> immediate
    assert veto_window_elapsed(100.0, 60, now=130.0) is False     # 30s < 60s
    assert veto_window_elapsed(100.0, 60, now=170.0) is True      # 70s >= 60s


# --- U31: hash-chained audit log -------------------------------------------

def test_audit_genesis_and_chain(tmp_path):
    a = AuditLog(OperatorState(root=tmp_path))
    r1 = a.append({"type": "x"})
    r2 = a.append({"type": "y"})
    assert r1["prev"] == "GENESIS"
    assert r2["prev"] == r1["hash"]


def test_audit_verify_detects_tampering(tmp_path):
    st = OperatorState(root=tmp_path)
    a = AuditLog(st)
    a.append({"type": "x"})
    a.append({"type": "y"})
    assert a.verify() is True
    rec = st.get("audit", "00000000")
    rec["event"] = {"type": "HACKED"}
    st.put("audit", "00000000", rec)
    assert a.verify() is False


def test_queue_writes_tamper_evident_audit(tmp_path):
    st = OperatorState(root=tmp_path)
    a = AuditLog(st)
    q = ApprovalQueue(st, audit=a)
    q.enqueue(_proposal(["post_external"], "p1"))
    q.approve("p1")
    assert a.verify() is True
    assert len(st.list("audit")) >= 2
