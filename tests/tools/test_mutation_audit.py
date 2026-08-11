# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D06: append-only mutation audit tests."""

import json

import pytest

from tools import memory_tool
from tools import mutation_audit
from tools import skill_manager_tool

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolated_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    # Force the memory write-approval gate OFF. This suite asserts the
    # direct-write audit path; if an earlier test in the same xdist worker
    # left a config (or the load_config cache) with the gate enabled, writes
    # would be staged instead of written, and no audit record would appear.
    from tools import write_approval

    monkeypatch.setattr(write_approval, "write_approval_enabled", lambda subsystem: False)
    # Reset any leaked write-origin ContextVar (set by agent-sediment/background
    # review tests in this worker thread). Without this, an earlier test that
    # set the origin without resetting it makes every audit record here carry
    # origin='assistant_tool'/'background_review' instead of 'foreground'.
    from tools import skill_provenance

    skill_provenance.set_current_write_origin("foreground")
    # Memory store path follows XAVANI_HOME.
    return tmp_path


def test_memory_add_writes_audit_record(tmp_path):
    store = memory_tool.MemoryStore()
    result = memory_tool.memory_tool(
        action="add", target="memory", content="fact: the sky is blue", store=store
    )
    assert json.loads(result)["success"] is True
    records = mutation_audit.read_audit(str(tmp_path))
    assert len(records) == 1
    record = records[0]
    assert record["kind"] == "memory"
    assert record["action"] == "add"
    assert record["target"] == "memory"
    assert record["origin"] == "foreground"
    assert record["success"] is True
    assert "the sky is blue" in record["preview"]


def test_memory_replace_writes_audit_record(tmp_path):
    store = memory_tool.MemoryStore()
    store.add("memory", "old fact")
    memory_tool.memory_tool(
        action="replace",
        target="memory",
        old_text="old fact",
        content="new fact",
        store=store,
    )
    records = mutation_audit.read_audit(str(tmp_path))
    assert records[-1]["action"] == "replace"
    assert records[-1]["success"] is True


def test_memory_failed_write_still_audited(tmp_path):
    store = memory_tool.MemoryStore()
    result = memory_tool.memory_tool(
        action="remove", target="memory", old_text="nothing here", store=store
    )
    records = mutation_audit.read_audit(str(tmp_path))
    assert records[-1]["action"] == "remove"
    assert records[-1]["success"] is False


def test_audit_never_raises_on_bad_path(monkeypatch):
    monkeypatch.setenv("XAVANI_HOME", "/nonexistent-dir-xavani-audit")
    mutation_audit.log_mutation("memory", "add", "memory", content="x")  # no raise


def test_read_audit_missing_file_returns_empty(tmp_path):
    assert mutation_audit.read_audit(str(tmp_path)) == []


def test_preview_is_truncated(tmp_path):
    mutation_audit.log_mutation(
        "memory", "add", "memory", content="x" * 1000, origin="test"
    )
    records = mutation_audit.read_audit(str(tmp_path))
    assert len(records[0]["preview"]) <= 200


def test_skill_create_writes_audit_with_origin(tmp_path, monkeypatch):
    from tools.skill_provenance import set_current_write_origin

    monkeypatch.setattr(skill_manager_tool, "SKILLS_DIR", tmp_path / "skills")
    token = set_current_write_origin("background_review")
    try:
        skill_manager_tool.skill_manage(
            action="create",
            name="audit-test-skill",
            content=(
                "---\nname: audit-test-skill\ndescription: audit test skill\n---\n# Body\n"
            ),
        )
    finally:
        from tools.skill_provenance import reset_current_write_origin

        reset_current_write_origin(token)
    records = mutation_audit.read_audit(str(tmp_path))
    assert records[-1]["kind"] == "skill"
    assert records[-1]["action"] == "create"
    assert records[-1]["origin"] == "background_review"
    assert records[-1]["success"] is True
