# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the memory/skill write-approval gate (tools/write_approval.py),
the memory_tool / skill_manager_tool gate integration, and the shared slash
command handlers (xavani_cli/write_approval_commands.py).

Covers the boolean write_approval gate (off by default = write freely; on =
require approval) for both subsystems, the foreground-vs-background staging
split, pending store CRUD, the list/approve/reject/diff/approval subcommand
dispatch, and approved-pending replay (apply_memory_pending /
apply_skill_pending).
"""

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def xavani_home(tmp_path, monkeypatch):
    """Point XAVANI_HOME at a fresh temp dir so the pending store, memory
    files, and skills all land in isolation for each test."""
    home = tmp_path / "xavani"
    monkeypatch.setenv("XAVANI_HOME", str(home))
    return home


@pytest.fixture
def skill_dir(tmp_path, monkeypatch):
    """Patch SKILLS_DIR and get_all_skills_dirs so skill writes/reads land in
    the temp dir instead of the real ~/.xavani/skills/.

    SKILLS_DIR is resolved at module import time, so the XAVANI_HOME env var
    alone is not enough once the module is loaded.
    """
    target = tmp_path / "skills"
    with patch("tools.skill_manager_tool.SKILLS_DIR", target), \
         patch("agent.skill_utils.get_all_skills_dirs", return_value=[target]):
        yield target


def _set_approval(monkeypatch, subsystem, enabled):
    """Make write_approval_enabled(subsystem) read `enabled` from config."""
    import xavani_cli.config as cfg
    monkeypatch.setattr(
        cfg, "load_config", lambda: {subsystem: {"write_approval": enabled}}
    )


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------

def test_default_gate_is_off(xavani_home):
    from tools import write_approval as wa
    # Default: gate off → writes flow freely.
    assert wa.write_approval_enabled("memory") is False
    assert wa.write_approval_enabled("skills") is False


def test_invalid_subsystem_is_off(xavani_home):
    from tools import write_approval as wa
    assert wa.write_approval_enabled("bogus") is False


def test_normalize_enabled_coerces_values():
    from tools import write_approval as wa
    # Real bools pass through.
    assert wa._normalize_enabled(True) is True
    assert wa._normalize_enabled(False) is False
    # Truthy strings → True (incl. legacy 'approve').
    assert wa._normalize_enabled("on") is True
    assert wa._normalize_enabled("approve") is True
    assert wa._normalize_enabled("true") is True
    # Everything else → False (gate off is the safe default).
    assert wa._normalize_enabled("off") is False
    assert wa._normalize_enabled("garbage") is False
    assert wa._normalize_enabled(None) is False


def test_gate_off_never_stages(xavani_home):
    from tools import write_approval as wa
    assert wa.evaluate_gate(wa.MEMORY).allow is True
    assert wa.evaluate_gate(wa.SKILLS).allow is True
    assert wa.pending_count("memory") == 0
    assert wa.pending_count("skills") == 0


# ---------------------------------------------------------------------------
# Pending store CRUD
# ---------------------------------------------------------------------------

def test_stage_list_get_discard(xavani_home):
    from tools import write_approval as wa

    rec = wa.stage_write(
        wa.MEMORY,
        {"action": "add", "target": "user", "content": "hello"},
        summary="add to user profile",
        origin="foreground",
    )
    assert rec["id"]
    assert rec["subsystem"] == "memory"
    assert wa.pending_count("memory") == 1

    listed = wa.list_pending(wa.MEMORY)
    assert len(listed) == 1
    assert listed[0]["id"] == rec["id"]
    assert listed[0]["summary"] == "add to user profile"

    got = wa.get_pending(wa.MEMORY, rec["id"])
    assert got is not None
    assert got["payload"]["content"] == "hello"
    assert got["origin"] == "foreground"

    assert wa.get_pending(wa.MEMORY, "nope") is None

    assert wa.discard_pending(wa.MEMORY, rec["id"]) is True
    assert wa.pending_count("memory") == 0
    assert wa.list_pending(wa.MEMORY) == []
    # Discarding a missing record reports False.
    assert wa.discard_pending(wa.MEMORY, rec["id"]) is False


def test_pending_subsystems_are_isolated(xavani_home):
    from tools import write_approval as wa
    wa.stage_write(wa.SKILLS, {"action": "create", "name": "s"},
                   summary="create 's'", origin="foreground")
    assert wa.pending_count("skills") == 1
    assert wa.pending_count("memory") == 0
    assert wa.list_pending(wa.MEMORY) == []


def test_pending_records_live_under_xavani_home(xavani_home):
    from tools import write_approval as wa
    rec = wa.stage_write(wa.MEMORY, {"action": "add", "target": "memory", "content": "x"},
                         summary="x", origin="foreground")
    assert (xavani_home / "pending" / "memory" / f"{rec['id']}.json").exists()


# ---------------------------------------------------------------------------
# Gate decision matrix
# ---------------------------------------------------------------------------

def test_memory_gate_on_stages_without_interactive_channel(xavani_home, monkeypatch):
    from tools import write_approval as wa
    _set_approval(monkeypatch, "memory", True)

    decision = wa.evaluate_gate(wa.MEMORY, inline_summary="add to user profile",
                                inline_detail="hello")
    assert decision.stage is True
    assert decision.allow is False
    assert "memory.write_approval" in decision.message


def test_skills_gate_on_always_stages(xavani_home, monkeypatch):
    from tools import write_approval as wa
    _set_approval(monkeypatch, "skills", True)

    decision = wa.evaluate_gate(wa.SKILLS)
    assert decision.stage is True
    assert decision.allow is False
    assert "skills.write_approval" in decision.message


def test_memory_inline_approval_allows(xavani_home, monkeypatch):
    from tools import write_approval as wa
    from tools import terminal_tool
    _set_approval(monkeypatch, "memory", True)

    def cb(command, description, allow_permanent=False):
        return "once"

    monkeypatch.setattr(terminal_tool, "_get_approval_callback", lambda: cb)
    decision = wa.evaluate_gate(wa.MEMORY, inline_summary="s", inline_detail="d")
    assert decision.allow is True


def test_memory_inline_denial_blocks(xavani_home, monkeypatch):
    from tools import write_approval as wa
    from tools import terminal_tool
    _set_approval(monkeypatch, "memory", True)

    def cb(command, description, allow_permanent=False):
        return "deny"

    monkeypatch.setattr(terminal_tool, "_get_approval_callback", lambda: cb)
    decision = wa.evaluate_gate(wa.MEMORY, inline_summary="s", inline_detail="d")
    assert decision.blocked is True
    assert "denied" in decision.message


def test_background_origin_stages_even_with_callback(xavani_home, monkeypatch):
    from tools import write_approval as wa
    from tools import terminal_tool
    from tools.skill_provenance import set_current_write_origin, reset_current_write_origin
    _set_approval(monkeypatch, "memory", True)
    monkeypatch.setattr(terminal_tool, "_get_approval_callback",
                        lambda: (lambda *a, **k: "once"))

    token = set_current_write_origin("background_review")
    try:
        assert wa.is_background() is True
        decision = wa.evaluate_gate(wa.MEMORY, inline_summary="s", inline_detail="d")
        assert decision.stage is True
    finally:
        reset_current_write_origin(token)


# ---------------------------------------------------------------------------
# Skill gist / diff helpers
# ---------------------------------------------------------------------------

_SKILL = (
    "---\nname: test-skill\ndescription: A test skill\nversion: 1.0.0\n---\n"
    "# Test\nbody\n"
)


def test_skill_gist_variants():
    from tools import write_approval as wa
    assert "create 's' — A test skill" in wa.skill_gist("create", "s", content=_SKILL)
    assert "patch 's' SKILL.md (+1/-1 lines)" == wa.skill_gist(
        "patch", "s", old_string="a", new_string="b")
    assert "write refs/x.md in 's'" == wa.skill_gist("write_file", "s", file_path="refs/x.md")
    assert "delete skill 's'" == wa.skill_gist("delete", "s")
    assert wa.skill_gist("bogus", "s") == "bogus 's'"


def test_frontmatter_description_extraction():
    from tools import write_approval as wa
    assert wa._frontmatter_description(_SKILL) == "A test skill"
    assert wa._frontmatter_description("# no frontmatter") == ""


def test_skill_pending_diff_create_returns_content(xavani_home):
    from tools import write_approval as wa
    rec = wa.stage_write(wa.SKILLS, {"action": "create", "name": "s", "content": _SKILL},
                         summary="create 's'", origin="foreground")
    assert wa.skill_pending_diff(rec) == _SKILL


def test_skill_pending_diff_patch_against_disk(xavani_home, skill_dir):
    from tools import write_approval as wa
    from tools.skill_manager_tool import skill_manage
    # Create the skill with the gate off so it lands on disk.
    r = json.loads(skill_manage("create", "test-skill", content=_SKILL))
    assert r["success"] is True, r

    rec = wa.stage_write(
        wa.SKILLS,
        {"action": "patch", "name": "test-skill", "file_path": "SKILL.md",
         "old_string": "body", "new_string": "new body"},
        summary="patch", origin="foreground",
    )
    diff = wa.skill_pending_diff(rec)
    assert "-body" in diff
    assert "+new body" in diff


# ---------------------------------------------------------------------------
# memory_tool integration
# ---------------------------------------------------------------------------

@pytest.fixture
def mem_store(xavani_home):
    from tools.memory_tool import MemoryStore
    s = MemoryStore(memory_char_limit=500, user_char_limit=300)
    s.load_from_disk()
    return s


def test_memory_gate_off_allows_write(xavani_home, mem_store):
    from tools.memory_tool import memory_tool
    from tools import write_approval as wa
    r = json.loads(memory_tool("add", "user", "save me", store=mem_store))
    assert r["success"] is True
    assert "save me" in mem_store.user_entries
    assert wa.pending_count("memory") == 0


def test_memory_gate_on_stages_and_does_not_write(xavani_home, monkeypatch, mem_store):
    from tools.memory_tool import memory_tool
    from tools import write_approval as wa
    _set_approval(monkeypatch, "memory", True)

    r = json.loads(memory_tool("add", "memory", "remember the launch date", store=mem_store))
    assert r["success"] is True
    assert r.get("staged") is True
    assert r.get("pending_id")
    assert wa.pending_count("memory") == 1
    # Nothing was committed to the store.
    assert mem_store.memory_entries == []
    # The staged payload can be replayed to the same store.
    rec = wa.get_pending(wa.MEMORY, r["pending_id"])
    from tools.memory_tool import apply_memory_pending
    applied = apply_memory_pending(rec["payload"], mem_store)
    assert applied["success"] is True
    assert "remember the launch date" in mem_store.memory_entries


def test_memory_gate_on_inline_approval_writes(xavani_home, monkeypatch, mem_store):
    from tools.memory_tool import memory_tool
    from tools import write_approval as wa
    from tools import terminal_tool
    _set_approval(monkeypatch, "memory", True)

    def cb(command, description, allow_permanent=False):
        return "once"

    monkeypatch.setattr(terminal_tool, "_get_approval_callback", lambda: cb)
    r = json.loads(memory_tool("add", "memory", "approved inline", store=mem_store))
    assert r["success"] is True
    assert "approved inline" in mem_store.memory_entries
    assert wa.pending_count("memory") == 0


def test_memory_gate_on_inline_denial_blocks(xavani_home, monkeypatch, mem_store):
    from tools.memory_tool import memory_tool
    from tools import write_approval as wa
    from tools import terminal_tool
    _set_approval(monkeypatch, "memory", True)

    def cb(command, description, allow_permanent=False):
        return "deny"

    monkeypatch.setattr(terminal_tool, "_get_approval_callback", lambda: cb)
    r = json.loads(memory_tool("add", "memory", "denied entry", store=mem_store))
    assert r["success"] is False
    assert "denied" in r.get("error", "")
    assert mem_store.memory_entries == []
    assert wa.pending_count("memory") == 0


# ---------------------------------------------------------------------------
# skill_manager_tool integration
# ---------------------------------------------------------------------------

def test_skill_gate_off_creates(xavani_home, skill_dir):
    from tools.skill_manager_tool import skill_manage
    from tools import write_approval as wa
    r = json.loads(skill_manage("create", "test-skill", content=_SKILL))
    assert r["success"] is True, r
    assert wa.pending_count("skills") == 0


def test_skill_gate_on_stages_create(xavani_home, monkeypatch, skill_dir):
    from tools.skill_manager_tool import skill_manage
    from tools import write_approval as wa
    _set_approval(monkeypatch, "skills", True)

    r = json.loads(skill_manage("create", "test-skill", content=_SKILL))
    assert r["success"] is True
    assert r.get("staged") is True
    assert r.get("pending_id")
    assert "create 'test-skill'" in r.get("gist", "")
    assert wa.pending_count("skills") == 1
    # The skill was NOT created on disk.
    assert not (skill_dir / "test-skill").exists()


def test_skill_gate_on_stages_patch(xavani_home, monkeypatch, skill_dir):
    from tools.skill_manager_tool import skill_manage
    from tools import write_approval as wa
    # Land the skill first (gate off), then gate a patch.
    assert json.loads(skill_manage("create", "test-skill", content=_SKILL))["success"]
    _set_approval(monkeypatch, "skills", True)

    r = json.loads(skill_manage(
        "patch", "test-skill", old_string="body", new_string="patched body"))
    assert r.get("staged") is True
    assert wa.pending_count("skills") == 1
    # On-disk content unchanged.
    on_disk = (skill_dir / "test-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "body" in on_disk
    assert "patched body" not in on_disk


def test_skill_approve_replays_without_regating(xavani_home, monkeypatch, skill_dir):
    from tools.skill_manager_tool import skill_manage, apply_skill_pending
    from tools import write_approval as wa
    _set_approval(monkeypatch, "skills", True)

    r = json.loads(skill_manage("create", "test-skill", content=_SKILL))
    assert r.get("staged") is True
    rec = wa.get_pending(wa.SKILLS, r["pending_id"])

    # Replay bypasses the gate: succeeds while the gate is still ON.
    out = json.loads(apply_skill_pending(rec["payload"]))
    assert out["success"] is True, out
    assert (skill_dir / "test-skill" / "SKILL.md").exists()


def test_skill_gate_off_patch_passes_through(xavani_home, skill_dir):
    from tools.skill_manager_tool import skill_manage
    from tools import write_approval as wa
    assert json.loads(skill_manage("create", "test-skill", content=_SKILL))["success"]
    r = json.loads(skill_manage("patch", "test-skill", old_string="body",
                                new_string="patched body"))
    assert r["success"] is True, r
    assert wa.pending_count("skills") == 0


# ---------------------------------------------------------------------------
# Shared command handler (xavani_cli/write_approval_commands.py)
# ---------------------------------------------------------------------------

def test_handle_pending_list_empty(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    out = handle_pending_subcommand(wa.MEMORY, ["pending"])
    assert out == "No pending memory writes."


def test_handle_bare_memory_shows_state_and_pending(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    out = handle_pending_subcommand(wa.MEMORY, [])
    assert "memory.write_approval = off" in out
    assert "No pending memory writes." in out


def test_handle_approve_all(xavani_home, mem_store):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    wa.stage_write(wa.MEMORY, {"action": "add", "target": "user", "content": "a"},
                   summary="a", origin="foreground")
    wa.stage_write(wa.MEMORY, {"action": "add", "target": "user", "content": "b"},
                   summary="b", origin="foreground")
    out = handle_pending_subcommand(wa.MEMORY, ["approve", "all"], memory_store=mem_store)
    assert "Approved 2" in out
    assert wa.pending_count("memory") == 0
    assert len(mem_store.user_entries) == 2


def test_handle_approve_unknown_id(xavani_home, mem_store):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    wa.stage_write(wa.MEMORY, {"action": "add", "target": "user", "content": "a"},
                   summary="a", origin="foreground")
    out = handle_pending_subcommand(wa.MEMORY, ["approve", "nope"], memory_store=mem_store)
    assert "No pending memory write with id 'nope'" in out
    # The staged write is untouched.
    assert wa.pending_count("memory") == 1


def test_handle_reject(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    rec = wa.stage_write(wa.SKILLS, {"action": "create", "name": "s", "content": _SKILL},
                         summary="create 's'", origin="foreground")
    out = handle_pending_subcommand(wa.SKILLS, ["reject", rec["id"]])
    assert f"Rejected pending skills write '{rec['id']}'." in out
    assert wa.pending_count("skills") == 0


def test_handle_reject_all(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    wa.stage_write(wa.SKILLS, {"action": "create", "name": "s", "content": _SKILL},
                   summary="s", origin="foreground")
    wa.stage_write(wa.SKILLS, {"action": "create", "name": "s2", "content": _SKILL},
                   summary="s2", origin="foreground")
    out = handle_pending_subcommand(wa.SKILLS, ["reject", "all"])
    assert "Rejected 2" in out
    assert wa.pending_count("skills") == 0


def test_handle_diff(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    rec = wa.stage_write(wa.SKILLS, {"action": "create", "name": "s", "content": _SKILL},
                         summary="create 's'", origin="foreground")
    out = handle_pending_subcommand(wa.SKILLS, ["diff", rec["id"]])
    assert "# Pending skill write" in out
    assert "name: test-skill" in out


def test_handle_approval_on(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    captured = {}
    out = handle_pending_subcommand(
        wa.MEMORY, ["approval", "on"],
        set_mode_fn=lambda enabled: captured.update(enabled=enabled),
    )
    assert captured["enabled"] is True
    assert "on" in out


def test_handle_approval_off(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    captured = {}
    out = handle_pending_subcommand(
        wa.SKILLS, ["approval", "off"],
        set_mode_fn=lambda enabled: captured.update(enabled=enabled),
    )
    assert captured["enabled"] is False
    assert "off" in out


def test_handle_approval_invalid_value(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    out = handle_pending_subcommand(wa.MEMORY, ["approval", "maybe"])
    assert "Invalid value" in out


def test_handle_unknown_subcommand_returns_none(xavani_home):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    assert handle_pending_subcommand(wa.MEMORY, ["frobnicate"]) is None
    assert handle_pending_subcommand(wa.SKILLS, ["search", "docker"]) is None


def test_skills_approve_replays_via_handler(xavani_home, monkeypatch, skill_dir):
    from xavani_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa
    _set_approval(monkeypatch, "skills", True)
    from tools.skill_manager_tool import skill_manage
    r = json.loads(skill_manage("create", "test-skill", content=_SKILL))
    assert r.get("staged") is True

    out = handle_pending_subcommand(wa.SKILLS, ["approve", r["pending_id"]])
    assert "Approved 1" in out
    assert wa.pending_count("skills") == 0
    assert (skill_dir / "test-skill" / "SKILL.md").exists()
