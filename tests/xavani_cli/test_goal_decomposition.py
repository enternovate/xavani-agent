# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B10: goal decomposition with progress tracking."""

import pytest

from xavani_cli.goals import GoalManager, GoalState, decompose_goal

pytestmark = pytest.mark.integration


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """GoalManager with an isolated session DB."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path / "home"))
    from xavani_cli import goals as goals_mod

    goals_mod._DB_CACHE.clear()
    yield GoalManager("test-session")
    goals_mod._DB_CACHE.clear()


# ── decompose_goal ──────────────────────────────────────────────────


def test_decompose_numbered_list():
    goal = "Build the feature:\n1. Write the backend\n2. Write the frontend\n3. Ship it"
    parts = decompose_goal(goal)
    assert len(parts) == 3
    assert parts[0] == "Write the backend"
    assert parts[-1] == "Ship it"


def test_decompose_bulleted_list():
    goal = "Plan the release:\n- Audit deps\n- Update changelog\n- Tag version"
    parts = decompose_goal(goal)
    assert len(parts) == 3
    assert "Audit deps" in parts


def test_decompose_semicolon_clauses():
    goal = "Fix the bug; add a regression test; run the suite"
    parts = decompose_goal(goal)
    assert len(parts) == 3
    assert parts[0] == "Fix the bug"


def test_decompose_single_statement_returns_empty():
    assert decompose_goal("Write a summary of the meeting") == []


def test_decompose_empty_returns_empty():
    assert decompose_goal("") == []
    assert decompose_goal("   ") == []


def test_decompose_caps_limit():
    goal = "\n".join(f"{i}. step {i}" for i in range(1, 12))
    assert len(decompose_goal(goal)) == 6


# ── auto-decomposition on set ───────────────────────────────────────


def test_set_auto_decomposes_complex_goal(manager):
    state = manager.set("Do all of this:\n1. Step one\n2. Step two")
    assert state.status == "active"
    assert len(state.subgoals) == 2
    assert state.subgoals[0]["status"] == "pending"


def test_set_keeps_simple_goal_undecomposed(manager):
    state = manager.set("Just do the one thing")
    assert state.subgoals == []


def test_set_with_auto_decompose_disabled(manager):
    state = manager.set(
        "Do this:\n1. A\n2. B", auto_decompose=False
    )
    assert state.subgoals == []


# ── status tracking ─────────────────────────────────────────────────


def test_mark_subgoal_done(manager):
    state = manager.set("Plan:\n1. Research\n2. Implement")
    returned = manager.mark_subgoal(1)
    assert returned == "Research"
    assert state.subgoals[0]["status"] == "done"
    assert state.subgoals[1]["status"] == "pending"


def test_mark_subgoal_out_of_range(manager):
    manager.set("Plan:\n1. Research")
    with pytest.raises(IndexError):
        manager.mark_subgoal(5)


def test_subgoal_progress_counts(manager):
    manager.set("Plan:\n1. A\n2. B\n3. C")
    manager.mark_subgoal(1)
    manager.mark_subgoal(2)
    progress = manager.subgoal_progress()
    assert progress == {
        "total": 3,
        "done": 2,
        "remaining": 1,
        "statuses": ["done", "done", "pending"],
    }


def test_subgoal_progress_empty(manager):
    manager.set("Simple goal")
    assert manager.subgoal_progress()["total"] == 0


# ── persistence roundtrip (dict subgoals) ───────────────────────────


def test_state_roundtrip_preserves_status(manager, tmp_path):
    manager.set("Plan:\n1. A\n2. B")
    manager.mark_subgoal(1)
    reloaded = GoalState.from_json(manager.state.to_json())
    assert reloaded.subgoals[0]["status"] == "done"
    assert reloaded.subgoals[1]["text"] == "B"
    assert reloaded.subgoals[1]["status"] == "pending"


def test_legacy_string_subgoals_preserved():
    """Back-compat: plain-string subgoals round-trip unchanged."""
    state = GoalState.from_json(
        '{"goal": "x", "status": "active", "subgoals": ["legacy one", "legacy two"]}'
    )
    assert state.subgoals == ["legacy one", "legacy two"]


def test_render_shows_done_marker(manager):
    manager.set("Plan:\n1. A\n2. B")
    manager.mark_subgoal(1)
    block = manager.state.render_subgoals_block()
    assert "✓" in block
    assert "1. A ✓" in block
    assert "2. B" in block
