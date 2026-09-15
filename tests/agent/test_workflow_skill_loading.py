# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Microcycle tests for explicit workflow skill loading (R3 Task 17).

Skills resolve through the existing discovery rules: the fixtures install the
real canonical catalog paths under a patched ``SKILLS_DIR`` and let
``skill_view`` resolve them.
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent import workflow_skills as ws
from agent.workflow_catalog import WORKFLOWS
from agent.workflow_skills import (
    RELOAD_INSTRUCTION,
    SMALL_CONTEXT_TOKENS,
    WorkflowSkillError,
    WorkflowSkillState,
    ensure_workflow_skills_loaded,
    record_selection,
    refresh_workflow_skills_at_boundary,
    retain_workflow_receipts,
    select_workflow,
    workflow_context_block,
    workflow_state,
)

FINANCE_SKILLS = tuple(WORKFLOWS["finance"].skills)


def _write_skill(root: Path, canonical_path: str, body: str, name: str = "") -> Path:
    target = Path(root) / canonical_path
    target.parent.mkdir(parents=True, exist_ok=True)
    skill_name = name or Path(canonical_path).parent.name
    target.write_text(
        "---\n"
        f"name: {skill_name}\n"
        f"description: synthetic {skill_name} skill for tests.\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return target


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_profile_config(body: str) -> None:
    """Write the active profile's config.yaml (XAVANI_HOME is per-test)."""
    from xavani_constants import get_config_path

    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


@pytest.fixture()
def skills_root(tmp_path):
    """Install the finance workflow's declared skills under a patched root."""
    root = tmp_path / "skills-root"
    root.mkdir()
    for index, canonical in enumerate(FINANCE_SKILLS):
        _write_skill(root, canonical, f"finance body {index}")
    with patch("tools.skills_tool.SKILLS_DIR", root):
        yield root


class _StubAgent:
    """Minimal host surface: receipt store plus a cached system prompt."""

    def __init__(self):
        self._workflow_skill_state = WorkflowSkillState()
        self._cached_system_prompt = "SYSTEM PROMPT SENTINEL"
        self._build_system_prompt = MagicMock(name="_build_system_prompt")
        self._invalidate_system_prompt = MagicMock(name="_invalidate_system_prompt")


def _receipts_by_path(agent):
    return {receipt.path: receipt for receipt in agent._workflow_skill_state.receipts()}


# ── 1. Selecting Finance resolves the declared skill files ─────────────────


def test_finance_selection_resolves_declared_skill_files(skills_root):
    selection = select_workflow("finance", mode="ask")

    assert tuple(skill.path for skill in selection.skills) == FINANCE_SKILLS
    assert selection.name == "Finance analysis"
    assert selection.checks == tuple(WORKFLOWS["finance"].checks)
    for index, skill in enumerate(selection.skills):
        assert Path(skill.resolved).is_file()
        assert skill.sha256 == _sha256(Path(skill.resolved))
        assert f"finance body {index}" in skill.content
    assert not selection.missing
    assert not selection.blocked


# ── 2. A missing required skill blocks Build mode ──────────────────────────


def test_missing_required_skill_blocks_build_mode(skills_root):
    (skills_root / FINANCE_SKILLS[1]).unlink()

    with pytest.raises(WorkflowSkillError) as excinfo:
        select_workflow("finance", mode="build")

    error = excinfo.value
    assert error.workflow_id == "finance"
    assert error.identifier == FINANCE_SKILLS[1]
    assert error.reason == "missing"
    assert str(error).startswith("Required skill unavailable:")


# ── 3. Ask mode can explain the missing prerequisite ───────────────────────


def test_ask_mode_explains_the_missing_prerequisite(skills_root):
    (skills_root / FINANCE_SKILLS[1]).unlink()

    selection = select_workflow("finance", mode="ask")

    assert selection.blocked is False
    assert [item.identifier for item in selection.missing] == [FINANCE_SKILLS[1]]
    assert [item.reason for item in selection.missing] == ["missing"]
    # The available skills still load — the explanation accompanies them.
    assert tuple(skill.path for skill in selection.skills) == (
        FINANCE_SKILLS[0],
        FINANCE_SKILLS[2],
    )

    explanation = selection.explanation()
    assert FINANCE_SKILLS[1] in explanation
    assert "Finance analysis" in explanation
    assert "build mode stays blocked" in explanation
    assert "skills.workflow_overrides" in explanation


# ── 4. A disabled skill does not load silently ─────────────────────────────


def test_disabled_skill_does_not_load_silently(skills_root):
    disabled_name = Path(FINANCE_SKILLS[1]).parent.name
    _write_profile_config(f"skills:\n  disabled:\n    - {disabled_name}\n")

    selection = select_workflow("finance", mode="ask")

    assert FINANCE_SKILLS[1] not in [skill.path for skill in selection.skills]
    assert [item.reason for item in selection.missing] == ["disabled"]

    with pytest.raises(WorkflowSkillError) as excinfo:
        select_workflow("finance", mode="build")

    assert excinfo.value.reason == "disabled"
    assert "disabled" in str(excinfo.value)


# ── 5. The host records the loaded content hash ────────────────────────────


def test_host_records_the_loaded_content_hash(skills_root):
    agent = _StubAgent()
    selection = select_workflow("finance", mode="ask")

    receipts = record_selection(agent, selection)

    assert len(receipts) == len(FINANCE_SKILLS)
    assert [receipt.path for receipt in receipts] == list(FINANCE_SKILLS)
    for receipt, skill in zip(receipts, selection.skills):
        assert receipt.sha256 == skill.sha256
        assert receipt.sha256 == _sha256(Path(receipt.resolved))
        assert receipt.origin == "host"
        assert receipt.loaded_at

    block = workflow_context_block(agent)
    for receipt in receipts:
        assert f"{receipt.path} sha256:{receipt.sha256}" in block


# ── 6. A skill edit takes effect at the next safe task boundary ────────────


def test_skill_edit_takes_effect_at_the_next_safe_task_boundary(skills_root):
    agent = _StubAgent()
    record_selection(agent, select_workflow("finance", mode="ask"))
    before = workflow_context_block(agent)
    digest_before = _receipts_by_path(agent)[FINANCE_SKILLS[1]].sha256

    target = skills_root / FINANCE_SKILLS[1]
    target.write_text(target.read_text(encoding="utf-8") + "\nExtra guidance.\n", encoding="utf-8")

    # Inside the active turn the loaded body and the receipt do not change.
    assert workflow_context_block(agent) == before
    assert _receipts_by_path(agent)[FINANCE_SKILLS[1]].sha256 == digest_before

    changed = refresh_workflow_skills_at_boundary(agent)

    assert changed == ((FINANCE_SKILLS[1], _sha256(target)),)
    assert _receipts_by_path(agent)[FINANCE_SKILLS[1]].sha256 == _sha256(target)
    assert workflow_context_block(agent) != before
    assert "finance body 1" in agent._workflow_skill_state.content(FINANCE_SKILLS[1])


# ── 7. Compression retains the receipt and reload instruction ──────────────


def test_compression_retains_the_receipt_and_reload_instruction(skills_root):
    agent = _StubAgent()
    record_selection(agent, select_workflow("finance", mode="ask"))
    messages = []

    assert retain_workflow_receipts(agent, messages) is True

    assert agent._workflow_skill_state.all_pruned()
    retained = messages[-1]["content"]
    for path in FINANCE_SKILLS:
        assert path in retained
        assert f"state:pruned" in retained
    assert RELOAD_INSTRUCTION in retained
    assert "skill_view(" in retained


class _CompressorStub:
    def __init__(self):
        self._last_compress_aborted = False
        self._last_summary_error = None
        self.compression_count = 0
        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0

    def compress(self, messages, current_tokens=None, focus_topic=None, force=False):
        return [{"role": "assistant", "content": "[CONTEXT SUMMARY]: compacted"}]


class _TodoStub:
    def format_for_injection(self):
        return ""


class _CompressionAgent:
    """Host surface required by agent.conversation_compression.compress_context."""

    log_prefix = ""
    platform = "cli"

    def __init__(self, state):
        self.session_id = "workflow-compression-session"
        self.model = "test-model"
        self.tools = []
        self._cached_system_prompt = "SYS"
        self._memory_manager = None
        self._session_db = None
        self._todo_store = _TodoStub()
        self._workflow_skill_state = state
        self.context_compressor = _CompressorStub()

    def _emit_status(self, *args, **kwargs):
        pass

    def _emit_warning(self, *args, **kwargs):
        pass

    def _vprint(self, *args, **kwargs):
        pass

    def _invalidate_system_prompt(self):
        pass

    def _build_system_prompt(self, system_message):
        return "SYS"

    def commit_memory_session(self, messages):
        pass


def test_compress_context_keeps_the_workflow_receipt(skills_root, tmp_path, monkeypatch):
    from agent.conversation_compression import compress_context

    monkeypatch.setenv("XAVANI_COMPRESS_CHECKPOINT_DIR", str(tmp_path / "checkpoints"))

    state = WorkflowSkillState()
    agent = _CompressionAgent(state)
    record_selection(agent, select_workflow("finance", mode="ask"))

    compressed, _ = compress_context(
        agent,
        [{"role": "user", "content": "analyse the statements"}],
        "SYSTEM",
    )

    retained = [message["content"] for message in compressed if isinstance(message["content"], str)]
    assert any(FINANCE_SKILLS[0] in content and "sha256:" in content for content in retained)
    assert any(RELOAD_INSTRUCTION in content for content in retained)
    assert state.all_pruned()


# ── 8. A pruned skill body reloads before a consequential action ───────────


def test_pruned_skill_body_reloads_before_a_consequential_action(skills_root):
    agent = _StubAgent()
    record_selection(agent, select_workflow("finance", mode="ask"))
    retain_workflow_receipts(agent, [])

    assert agent._workflow_skill_state.all_pruned()

    reloaded = ensure_workflow_skills_loaded(agent)

    assert tuple(skill.path for skill in reloaded) == FINANCE_SKILLS
    assert not agent._workflow_skill_state.all_pruned()
    for skill in reloaded:
        assert skill.sha256 == _sha256(Path(skill.resolved))


def test_pruned_skill_body_that_cannot_be_reloaded_blocks_the_action(skills_root):
    agent = _StubAgent()
    record_selection(agent, select_workflow("finance", mode="ask"))
    retain_workflow_receipts(agent, [])
    (skills_root / FINANCE_SKILLS[2]).unlink()

    with pytest.raises(WorkflowSkillError) as excinfo:
        ensure_workflow_skills_loaded(agent)

    assert excinfo.value.identifier == FINANCE_SKILLS[2]
    assert _receipts_by_path(agent)[FINANCE_SKILLS[2]].pruned is True


# ── 9. A small context window loads only the current step's skills ─────────


def test_small_context_window_loads_only_the_current_step_skills(skills_root):
    wide = select_workflow("finance", mode="ask", context_window_tokens=SMALL_CONTEXT_TOKENS * 4)
    assert tuple(skill.path for skill in wide.skills) == FINANCE_SKILLS
    assert wide.deferred == ()
    assert wide.small_context is False

    narrow = select_workflow(
        "finance",
        mode="ask",
        step_index=1,
        context_window_tokens=SMALL_CONTEXT_TOKENS // 4,
    )

    assert narrow.small_context is True
    assert tuple(skill.path for skill in narrow.skills) == (FINANCE_SKILLS[1],)
    assert narrow.deferred == (FINANCE_SKILLS[0], FINANCE_SKILLS[2])
    assert narrow.step_index == 1


# ── 10. The system prompt stays byte-stable within the active turn ─────────


def test_system_prompt_stays_byte_stable_within_the_active_turn(skills_root):
    agent = _StubAgent()
    prompt_before = agent._cached_system_prompt

    selection = select_workflow("finance", mode="ask")
    record_selection(agent, selection)
    first_block = workflow_context_block(agent)
    second_block = workflow_context_block(agent)

    assert first_block == second_block
    assert agent._cached_system_prompt is prompt_before
    agent._build_system_prompt.assert_not_called()
    agent._invalidate_system_prompt.assert_not_called()
    for skill in selection.skills:
        assert skill.path in first_block
        assert skill.path not in agent._cached_system_prompt


def test_skill_selection_creates_actual_loaded_context(skills_root):
    from agent.skill_commands import build_workflow_skill_message

    message = build_workflow_skill_message("finance", mode="ask")

    assert message is not None
    assert "Finance analysis" in message
    # Loaded bodies, not a suggestion list of names.
    for index, canonical in enumerate(FINANCE_SKILLS):
        assert canonical in message
        assert f"finance body {index}" in message
        assert _sha256(skills_root / canonical) in message
    assert "[Skill directory:" in message

    step_message = build_workflow_skill_message(
        "finance",
        mode="ask",
        step_index=2,
        context_window_tokens=SMALL_CONTEXT_TOKENS // 4,
    )
    assert step_message is not None
    assert "finance body 2" in step_message
    assert "finance body 0" not in step_message
    assert FINANCE_SKILLS[0] in step_message  # listed as deferred


# ── Resolution rules: discovery + profile override precedence ──────────────


def test_approved_profile_override_takes_precedence(skills_root):
    override_name = "approved/dcf-approved"
    _write_skill(skills_root, f"{override_name}/SKILL.md", "approved dcf body")
    _write_profile_config(
        "skills:\n  workflow_overrides:\n"
        f'    "{FINANCE_SKILLS[1]}": "{override_name}"\n'
    )

    selection = select_workflow("finance", mode="ask")

    skill = selection.skills[1]
    assert skill.path == FINANCE_SKILLS[1]
    assert "approved dcf body" in skill.content
    assert Path(skill.resolved) == (skills_root / override_name / "SKILL.md").resolve()
    assert skill.sha256 == _sha256(skills_root / override_name / "SKILL.md")


def test_unresolvable_override_does_not_fall_back_to_the_catalog_path(skills_root):
    _write_profile_config(
        "skills:\n  workflow_overrides:\n"
        f'    "{FINANCE_SKILLS[1]}": "approved/not-installed"\n'
    )

    selection = select_workflow("finance", mode="ask")

    assert [item.reason for item in selection.missing] == ["override_unavailable"]
    assert FINANCE_SKILLS[1] not in [skill.path for skill in selection.skills]


def test_same_named_skill_elsewhere_does_not_satisfy_the_canonical_path(skills_root):
    # Discovery resolves the whole relative path, so a stray "dcf-model" in
    # another category must not stand in for the canonical skill.
    _write_skill(skills_root, "stray/dcf-model/SKILL.md", "stray dcf body")
    (skills_root / FINANCE_SKILLS[1]).unlink()

    selection = select_workflow("finance", mode="ask")

    assert [item.reason for item in selection.missing] == ["missing"]
    assert [skill.path for skill in selection.skills] == [
        FINANCE_SKILLS[0],
        FINANCE_SKILLS[2],
    ]
    assert not any("stray dcf body" in skill.content for skill in selection.skills)


def test_pruned_or_empty_skill_content_is_refused(skills_root):
    target = skills_root / FINANCE_SKILLS[2]
    target.write_text(
        "---\nname: excel-author\ndescription: pruned.\n---\n\n[SKILL_PRUNED]\n",
        encoding="utf-8",
    )

    selection = select_workflow("finance", mode="ask")
    assert [item.reason for item in selection.missing] == ["pruned"]

    with pytest.raises(WorkflowSkillError) as excinfo:
        select_workflow("finance", mode="build")
    assert str(excinfo.value).startswith("Required skill content unavailable:")

    target.write_text("   \n", encoding="utf-8")
    selection = select_workflow("finance", mode="ask")
    assert [item.reason for item in selection.missing] == ["empty"]


def test_unknown_mode_and_workflow_are_rejected(skills_root):
    with pytest.raises(ValueError, match="Unknown mode"):
        select_workflow("finance", mode="deploy")
    with pytest.raises(ValueError, match="Unknown workflow"):
        select_workflow("payroll", mode="ask")


# ── Host wiring: agent init attaches the receipt store ─────────────────────


def test_agent_init_attaches_the_workflow_receipt_store():
    from unittest.mock import patch as _patch

    from run_agent import AIAgent
    from tests.harness.faux_provider import ScriptedSession

    openai_patch = _patch("run_agent.OpenAI", new=object())
    openai_patch.start()
    session = ScriptedSession()
    factory = session.client_factory()
    openai_patch.stop()
    provider_patch = _patch("run_agent.OpenAI", factory)
    provider_patch.start()
    try:
        with (
            _patch("run_agent.get_tool_definitions", return_value=[]),
            _patch("run_agent.check_toolset_requirements", return_value={}),
        ):
            agent = AIAgent(
                api_key="test-key-1234567890",
                base_url="https://openrouter.ai/api/v1",
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
            )
    finally:
        provider_patch.stop()

    assert isinstance(agent._workflow_skill_state, WorkflowSkillState)
    assert workflow_state(agent) is agent._workflow_skill_state
    assert workflow_state(agent).receipts() == ()


# ── Task 21 wiring: selector entry + loop boundary hook ────────────────────


def test_selector_entry_loads_records_and_formats(skills_root):
    from agent.skill_commands import select_workflow_for_agent

    agent = _StubAgent()
    result = select_workflow_for_agent(agent, "finance", mode="ask")

    assert result["workflow_id"] == "finance"
    assert "Finance analysis" in result["message"]
    assert "finance body 0" in result["message"]
    assert result["blocked"] is False
    receipts = _receipts_by_path(agent)
    assert set(receipts) == set(FINANCE_SKILLS)
    assert result["context_block"].startswith("[Workflow skill receipt")
    assert agent._workflow_skill_state.revision == 1


def test_boundary_hook_is_a_noop_without_a_selection(skills_root):
    from agent.conversation_loop import _apply_workflow_boundary

    agent = _StubAgent()
    messages = []
    _apply_workflow_boundary(agent, messages)
    assert messages == []


def test_boundary_hook_injects_once_and_surfaces_edits(skills_root):
    from agent.conversation_loop import _apply_workflow_boundary
    from agent.skill_commands import select_workflow_for_agent

    agent = _StubAgent()
    messages = []
    select_workflow_for_agent(agent, "finance", mode="ask")

    _apply_workflow_boundary(agent, messages)
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"].startswith("[Workflow skill receipt")

    # Unchanged store: no repeat injection on the next boundary.
    _apply_workflow_boundary(agent, messages)
    assert len(messages) == 1

    # An on-disk edit is applied and re-surfaced at the boundary.
    _write_skill(skills_root, FINANCE_SKILLS[0], "finance body 0 v2")
    _apply_workflow_boundary(agent, messages)
    assert len(messages) == 2
    receipts = _receipts_by_path(agent)
    assert receipts[FINANCE_SKILLS[0]].sha256 == _sha256(skills_root / FINANCE_SKILLS[0])


def test_boundary_hook_leaves_compression_retention_to_the_compression_path(skills_root):
    from agent.conversation_loop import _apply_workflow_boundary
    from agent.skill_commands import select_workflow_for_agent

    agent = _StubAgent()
    messages = []
    select_workflow_for_agent(agent, "finance", mode="ask")
    _apply_workflow_boundary(agent, messages)
    assert len(messages) == 1

    # Compression prunes the bodies and injects its own receipt+instruction;
    # the next task boundary must not spam another copy.
    retained: list = []
    retain_workflow_receipts(agent, retained)
    assert any(RELOAD_INSTRUCTION in m["content"] for m in retained)
    _apply_workflow_boundary(agent, messages)
    assert len(messages) == 1  # nothing new injected
    # The refresh re-reads reloadable bodies, so the store self-heals.
    assert agent._workflow_skill_state.all_pruned() is False


def test_consequential_selection_reloads_pruned_bodies(skills_root):
    from agent.skill_commands import select_workflow_for_agent

    agent = _StubAgent()
    select_workflow_for_agent(agent, "finance", mode="ask")
    agent._workflow_skill_state.mark_pruned()
    assert agent._workflow_skill_state.all_pruned() is True

    result = select_workflow_for_agent(agent, "finance", mode="build")
    assert result["consequential"] is True
    assert result["blocked"] is False
    assert agent._workflow_skill_state.all_pruned() is False
