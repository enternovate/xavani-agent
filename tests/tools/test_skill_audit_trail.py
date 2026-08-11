# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D11: audit trail for every skill modification.

Every skill write (create, edit, patch, write_file, remove_file, delete)
appends a JSONL record with before/after SHA-256 hashes so unauthorized
modifications leave a detectable gap.
"""

import json

import pytest

import xavani_skill_audit as audit
from xavani_skill_audit import (
    count_skill_audit,
    list_skill_audit,
    record_skill_change,
    skill_audit_enabled,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Point the audit trail and skill storage at per-test paths."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path / "home"))
    audit_path = tmp_path / "home" / "data" / "skill_audit.jsonl"
    monkeypatch.setattr(audit, "_audit_path", lambda: audit_path)
    # skill_manager_tool resolves SKILLS_DIR at import time from the real
    # home — patch it (and the multi-dir search) to the test sandbox so
    # mutations never touch the developer's real skills.
    skills_dir = tmp_path / "skills"
    monkeypatch.setattr(
        "tools.skill_manager_tool.SKILLS_DIR", skills_dir, raising=True
    )
    # _find_skill lazily imports get_all_skills_dirs from agent.skill_utils
    # — patch the source so the sandbox is the only search root.
    monkeypatch.setattr(
        "agent.skill_utils.get_all_skills_dirs",
        lambda: [skills_dir],
        raising=True,
    )
    yield audit_path
    try:
        audit_path.unlink(missing_ok=True)
    except OSError:
        pass


# ── module-level audit store ────────────────────────────────────────


def test_record_appends_jsonl(_isolated_home):
    ok = record_skill_change("edit", "my-skill", "SKILL.md", "abc", "def", True)
    assert ok is True
    line = _isolated_home.read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["action"] == "edit"
    assert rec["skill"] == "my-skill"
    assert rec["before_sha256"] == "abc"
    assert rec["after_sha256"] == "def"
    assert rec["success"] is True


def test_record_appends_multiple(_isolated_home):
    record_skill_change("create", "a")
    record_skill_change("edit", "a", before_sha256="x", after_sha256="y")
    assert len(list_skill_audit()) == 2


def test_list_newest_first(_isolated_home):
    record_skill_change("create", "a")
    record_skill_change("edit", "a")
    records = list_skill_audit()
    assert records[0]["action"] == "edit"
    assert records[1]["action"] == "create"


def test_list_limits(_isolated_home):
    for i in range(5):
        record_skill_change("edit", f"s{i}")
    assert len(list_skill_audit(limit=2)) == 2
    assert len(list_skill_audit(limit=100)) == 5


def test_count(_isolated_home):
    assert count_skill_audit() == 0
    record_skill_change("create", "a")
    assert count_skill_audit() == 1


def test_record_captures_actor_extra(_isolated_home):
    record_skill_change("patch", "s1", extra={"actor": "background_review"})
    rec = list_skill_audit()[0]
    assert rec["extra"]["actor"] == "background_review"


def test_disabled_by_env(_isolated_home, monkeypatch):
    monkeypatch.setenv("XAVANI_SKILL_AUDIT", "0")
    assert skill_audit_enabled() is False
    assert record_skill_change("edit", "s1") is False
    assert not _isolated_home.exists()


def test_missing_file_returns_empty(_isolated_home):
    assert list_skill_audit() == []
    assert count_skill_audit() == 0


# ── integration: skill_manage records every mutation ────────────────


SKILL_MD = """---
name: audit-test-skill
description: D11 integration test skill.
---

# Audit Test Skill
Body.
"""


def _run_skill_manage(action, name, **kwargs):
    from tools.skill_manager_tool import skill_manage

    return json.loads(skill_manage(action=action, name=name, **kwargs))


def test_create_records_audit(_isolated_home):
    result = _run_skill_manage("create", "audit-test-skill", content=SKILL_MD)
    assert result["success"] is True
    records = list_skill_audit()
    assert records[0]["action"] == "create"
    assert records[0]["skill"] == "audit-test-skill"
    assert records[0]["before_sha256"] is None
    assert records[0]["after_sha256"] is not None


def test_edit_records_before_after_hashes(_isolated_home):
    _run_skill_manage("create", "audit-test-skill", content=SKILL_MD)
    edited = SKILL_MD.replace("Body.", "Updated body.")
    result = _run_skill_manage("edit", "audit-test-skill", content=edited)
    assert result["success"] is True
    rec = list_skill_audit()[0]
    assert rec["action"] == "edit"
    assert rec["before_sha256"] != rec["after_sha256"]
    assert rec["success"] is True


def test_patch_records_audit(_isolated_home):
    _run_skill_manage("create", "audit-test-skill", content=SKILL_MD)
    result = _run_skill_manage(
        "patch", "audit-test-skill", old_string="Body.", new_string="Patched."
    )
    assert result["success"] is True
    rec = list_skill_audit()[0]
    assert rec["action"] == "patch"
    assert rec["before_sha256"] != rec["after_sha256"]


def test_write_file_records_audit(_isolated_home):
    _run_skill_manage("create", "audit-test-skill", content=SKILL_MD)
    result = _run_skill_manage(
        "write_file", "audit-test-skill",
        file_path="references/api.md", file_content="# API\n",
    )
    assert result["success"] is True
    rec = list_skill_audit()[0]
    assert rec["action"] == "write_file"
    assert rec["file"].endswith("references/api.md")
    assert rec["before_sha256"] is None  # new file
    assert rec["after_sha256"] is not None


def test_remove_file_records_audit(_isolated_home):
    _run_skill_manage("create", "audit-test-skill", content=SKILL_MD)
    _run_skill_manage(
        "write_file", "audit-test-skill",
        file_path="references/api.md", file_content="# API\n",
    )
    result = _run_skill_manage(
        "remove_file", "audit-test-skill", file_path="references/api.md"
    )
    assert result["success"] is True
    rec = list_skill_audit()[0]
    assert rec["action"] == "remove_file"
    assert rec["after_sha256"] is None


def test_delete_records_before_hash(_isolated_home):
    _run_skill_manage("create", "audit-test-skill", content=SKILL_MD)
    result = _run_skill_manage("delete", "audit-test-skill", absorbed_into="")
    assert result["success"] is True
    rec = list_skill_audit()[0]
    assert rec["action"] == "delete"
    assert rec["before_sha256"] is not None
    assert rec["after_sha256"] is None


def test_failed_mutation_records_failure(_isolated_home):
    result = _run_skill_manage("edit", "does-not-exist", content=SKILL_MD)
    assert result["success"] is False
    rec = list_skill_audit()[0]
    assert rec["action"] == "edit"
    assert rec["skill"] == "does-not-exist"
    assert rec["success"] is False
