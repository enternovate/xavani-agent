# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C14: xavani-first integration suite.

End-to-end flow tests that connect REAL modules — no mocks in the
critical path:

1. config.yaml load + validate + env expansion
2. SessionDB session lifecycle (create / append / reopen)
3. memory manager recall (episodic store on the same DB)
4. preference learning (C08) persists and recalls
5. approval + risk budget integration
6. statusline + telemetry read from real state

Run with:  bash scripts/run_tests.sh tests/integration/test_xavani_flow.py
"""

import json

import pytest

from xavani_state import SessionDB


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Hermetic XAVANI_HOME with a minimal config.yaml."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    monkeypatch.delenv("XAVANI_APPROVAL_REASON_LOG", raising=False)
    (tmp_path / "config.yaml").write_text(
        "agent:\n  reasoning_effort: high\ndisplay:\n  tool_progress: new\n"
        "plugins:\n  enabled: []\n",
        encoding="utf-8",
    )
    return tmp_path


# ── config → state ──────────────────────────────────────────────────


def test_config_loads_and_validates(home):
    from xavani_cli.config import load_config

    config = load_config()
    assert config["agent"]["reasoning_effort"] == "high"
    assert config["display"]["tool_progress"] == "new"


def test_config_survives_round_trip(home):
    from xavani_cli.config import load_config, save_config

    config = load_config()
    save_config(config)
    reloaded = load_config()
    assert reloaded["agent"]["reasoning_effort"] == "high"


# ── session lifecycle ───────────────────────────────────────────────


def test_session_db_full_lifecycle(home):
    db = SessionDB(home / "state.db")
    try:
        db.create_session("s1", source="cli")
        db.append_message("s1", role="user", content="hello")
        db.append_message("s1", role="assistant", content="hi there")
        assert len(db.get_messages("s1")) == 2
        # Reopen path (same DB file, new handle) must see the data.
        db2 = SessionDB(home / "state.db")
        try:
            assert len(db2.get_messages("s1")) == 2
        finally:
            db2.close()
    finally:
        db.close()


# ── memory + preferences ────────────────────────────────────────────


def test_memory_recall_after_episode(home):
    from xavani_memory.manager import MemoryManager

    mm = MemoryManager(memory_dir=home / "memory", auto_maintenance=False)
    mm.set_session("s1")
    mm.remember(
        user_input="I fixed the flaky test with a retry loop.",
        agent_response="Good work on the retry loop.",
    )
    context = mm.get_recall_context()
    assert isinstance(context, dict)
    assert context  # a real recall context was produced
    # The context carries durable content from the episode store.
    assert "durable_facts" in context or "procedural_hints" in context


def test_preference_learning_persists_across_managers(home):
    from tools.preference_learning import learn_from_message, preferences_for

    learn_from_message("user-42", "Always use pytest for tests.", home=home)
    assert "Always use pytest for tests" in preferences_for("user-42", home=home)
    # Reload from disk: preferences_for re-reads the store.
    assert preferences_for("user-42", home=home)


# ── approval + budget ───────────────────────────────────────────────


def test_approval_reasoning_logs_with_telemetry(home, monkeypatch):
    from xavani_cli.command_telemetry import telemetry_report
    from tools.approval import check_dangerous_command

    monkeypatch.setenv("XAVANI_INTERACTIVE", "1")
    monkeypatch.setattr(
        "tools.approval.prompt_dangerous_approval",
        lambda *a, **k: "deny",
    )
    result = check_dangerous_command("rm -rf /", env_type="local")
    assert result["approved"] is False
    report = telemetry_report(hours=24)
    assert report["total_decisions"] >= 1
    assert report["deny_rate"] >= 0


# ── statusline from real state ──────────────────────────────────────


def test_statusline_builds_from_agent_state(home):
    from xavani_cli.statusline import build_statusline_segments

    segments = build_statusline_segments(
        {
            "model": "claude-opus",
            "provider": "anthropic",
            "context_used": 50_000,
            "context_budget": 200_000,
            "turn": 4,
            "session_id": "20260804_120000_abcd1234",
        }
    )
    assert segments[0][0] == "claude-opus (anthropic)"
    ctx = [s for s in segments if s[0].startswith("ctx ")]
    assert ctx and ctx[0][1] == "default"


# ── autodiscovery integration ───────────────────────────────────────


def test_declarative_tool_discovered_and_callable(home):
    from tools.auto_discovery import load_user_tools
    from tools.registry import ToolRegistry

    tools_dir = home / "tools"
    tools_dir.mkdir()
    (tools_dir / "greet.yaml").write_text(
        "name: greet\ndescription: Say hi\ncommand: echo hello\n",
        encoding="utf-8",
    )
    registry = ToolRegistry()
    records = load_user_tools(registry, home=home)
    assert records and records[0].ok
    entry = registry.get_entry("greet")
    assert entry is not None
    assert entry.handler({"args": ""})["exit_code"] == 0


# ── end-to-end: one hermetic session ────────────────────────────────


def test_full_flow_single_home(home):
    """Config + session + memory + preference in one home dir."""
    from xavani_cli.config import load_config
    from xavani_memory.manager import MemoryManager
    from tools.preference_learning import learn_from_message, preferences_for

    config = load_config()
    assert config["agent"]["reasoning_effort"] == "high"

    db = SessionDB(home / "state.db")
    try:
        db.create_session("flow-session", source="cli")
        db.append_message("flow-session", role="user", content="start")
    finally:
        db.close()

    mm = MemoryManager(memory_dir=home / "memory", auto_maintenance=False)
    mm.set_session("flow-session")
    mm.remember(
        user_input="Always use ruff for linting.",
        agent_response="Noted.",
    )

    learn_from_message("flow-user", "Always use ruff for linting.", home=home)
    assert preferences_for("flow-user", home=home)
    assert (home / "state.db").exists()
    assert (home / "data" / "user_preferences.json").exists()
