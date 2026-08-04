# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A10: audit logging verbosity (XAVANI_AUDIT_LOG).

One key controls audit write volume:
  0 = off, 1 = decisions only, 2 = every request (default).
"""

import pytest

from xavani_operator.audit import AuditLog, audit_enabled, audit_verbosity


# ── verbosity resolution ─────────────────────────────────────────────


def test_default_verbosity_is_2(monkeypatch):
    monkeypatch.delenv("XAVANI_AUDIT_LOG", raising=False)
    assert audit_verbosity() == 2


@pytest.mark.parametrize("raw,expected", [("0", 0), ("1", 1), ("2", 2)])
def test_verbosity_parses_valid_levels(monkeypatch, raw, expected):
    monkeypatch.setenv("XAVANI_AUDIT_LOG", raw)
    assert audit_verbosity() == expected


def test_verbosity_clamps_out_of_range(monkeypatch):
    monkeypatch.setenv("XAVANI_AUDIT_LOG", "7")
    assert audit_verbosity() == 2
    monkeypatch.setenv("XAVANI_AUDIT_LOG", "-3")
    assert audit_verbosity() == 0


def test_verbosity_falls_back_on_garbage(monkeypatch):
    monkeypatch.setenv("XAVANI_AUDIT_LOG", "banana")
    assert audit_verbosity() == 2


def test_audit_enabled_thresholds(monkeypatch):
    monkeypatch.setenv("XAVANI_AUDIT_LOG", "1")
    assert audit_enabled(0) is True
    assert audit_enabled(1) is True
    assert audit_enabled(2) is False


# ── AuditLog.append gating ───────────────────────────────────────────


def test_append_dropped_at_level_0(monkeypatch, tmp_path):
    from xavani_operator.state import OperatorState

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "0")
    log = AuditLog(OperatorState(root=tmp_path))
    assert log.append({"type": "approve", "proposal": "p1"}) is None
    assert log.entries() == []


def test_append_decision_kept_at_level_1(monkeypatch, tmp_path):
    from xavani_operator.state import OperatorState

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "1")
    log = AuditLog(OperatorState(root=tmp_path))
    record = log.append({"type": "approve", "proposal": "p1"})
    assert record is not None
    assert record["event"]["type"] == "approve"
    assert log.verify() is True


def test_append_verbose_dropped_at_level_1(monkeypatch, tmp_path):
    from xavani_operator.state import OperatorState

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "1")
    log = AuditLog(OperatorState(root=tmp_path))
    assert log.append({"type": "tool_call"}, min_level=2) is None
    assert log.entries() == []


def test_append_verbose_kept_at_level_2(monkeypatch, tmp_path):
    from xavani_operator.state import OperatorState

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "2")
    log = AuditLog(OperatorState(root=tmp_path))
    record = log.append({"type": "tool_call"}, min_level=2)
    assert record is not None
    assert log.verify() is True


def test_approval_queue_decisions_audited_at_level_1(monkeypatch, tmp_path):
    from xavani_operator.approval_queue import ApprovalQueue
    from xavani_operator.propose import make_proposal
    from xavani_operator.state import OperatorState
    from xavani_operator.types import Intent, Opportunity

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "1")
    state = OperatorState(root=tmp_path)
    log = AuditLog(state)
    q = ApprovalQueue(state, audit=log)

    def gen(intent, ctx):
        return [{"action_class": "post_external", "summary": "x"}]

    intent = Intent(opportunity=Opportunity(id="o", kind="k", workstream="build", score=1.0))
    q.enqueue(make_proposal(intent, proposal_id="p1", generate=gen))
    q.approve("p1")

    events = [e["event"]["type"] for e in log.entries()]
    assert events == ["enqueue", "status"]
    assert log.verify() is True


def test_approval_queue_not_audited_at_level_0(monkeypatch, tmp_path):
    from xavani_operator.approval_queue import ApprovalQueue
    from xavani_operator.propose import make_proposal
    from xavani_operator.state import OperatorState
    from xavani_operator.types import Intent, Opportunity

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "0")
    state = OperatorState(root=tmp_path)
    log = AuditLog(state)
    q = ApprovalQueue(state, audit=log)

    def gen(intent, ctx):
        return [{"action_class": "post_external", "summary": "x"}]

    intent = Intent(opportunity=Opportunity(id="o", kind="k", workstream="build", score=1.0))
    q.enqueue(make_proposal(intent, proposal_id="p1", generate=gen))
    q.approve("p1")

    # Proposals still work; only the audit trail is silent.
    assert q.get("p1") is not None
    assert q.get("p1").status.value == "approved"
    assert log.entries() == []


# ── OAGAuditLogger gating ────────────────────────────────────────────


def _count_audit_rows(db_path):
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    finally:
        conn.close()


def test_oag_all_requests_at_level_2(monkeypatch, tmp_path):
    from gateway.oag_proxy import OAGAuditLogger

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "2")
    db = tmp_path / "audit.db"
    log = OAGAuditLogger(db)
    log.log("u1", "tool_a", "srv", "do x", 1.0, True)
    log.log("u1", "tool_b", "srv", "do y", 1.0, False, denied_reason="blocked")
    assert _count_audit_rows(db) == 2


def test_oag_denials_only_at_level_1(monkeypatch, tmp_path):
    from gateway.oag_proxy import OAGAuditLogger

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "1")
    db = tmp_path / "audit.db"
    log = OAGAuditLogger(db)
    log.log("u1", "tool_a", "srv", "do x", 1.0, True)
    log.log("u1", "tool_b", "srv", "do y", 1.0, False, denied_reason="blocked")
    # Only the denial (a decision) is on record.
    assert _count_audit_rows(db) == 1
    import sqlite3

    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute("SELECT allowed, denied_reason FROM audit_log").fetchone()
        assert row[0] == 0
        assert row[1] == "blocked"
    finally:
        conn.close()


def test_oag_nothing_at_level_0(monkeypatch, tmp_path):
    from gateway.oag_proxy import OAGAuditLogger

    monkeypatch.setenv("XAVANI_AUDIT_LOG", "0")
    db = tmp_path / "audit.db"
    log = OAGAuditLogger(db)
    log.log("u1", "tool_a", "srv", "do x", 1.0, True)
    log.log("u1", "tool_b", "srv", "do y", 1.0, False, denied_reason="blocked")
    assert _count_audit_rows(db) == 0
