# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G08: context prefetch tests."""

import subprocess

import pytest

from agent.context_prefetch import (
    build_prefetch_context,
    format_prefetch_block,
    git_repo_root,
    prefetch_git_state,
    prefetch_instincts,
    prefetch_session_facts,
)


@pytest.fixture
def git_repo(tmp_path):
    """A tiny git repo with a branch, changes, and commits."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "a.txt").write_text("one", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "first"], cwd=repo, check=True)
    (repo / "b.txt").write_text("two", encoding="utf-8")
    return repo


# ── git state ───────────────────────────────────────────────────────


def test_git_repo_root(git_repo):
    assert git_repo_root(str(git_repo)) == str(git_repo)


def test_git_repo_root_outside_repo(tmp_path):
    assert git_repo_root(str(tmp_path)) is None


def test_prefetch_git_state_shape(git_repo):
    state = prefetch_git_state(str(git_repo))
    assert state["repo_root"] == str(git_repo)
    assert state["branch"]  # main or master
    assert state["changed_files"] == 1  # b.txt untracked
    assert "b.txt" in state["status_preview"]
    assert state["recent_commits"][0].endswith("first")


def test_prefetch_git_state_empty_outside_repo(tmp_path):
    assert prefetch_git_state(str(tmp_path)) == {}


def test_prefetch_git_state_clean_repo(git_repo):
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "second"], cwd=git_repo, check=True)
    state = prefetch_git_state(str(git_repo))
    assert "changed_files" not in state
    assert len(state["recent_commits"]) == 2


# ── session facts + instincts ───────────────────────────────────────


def test_prefetch_session_facts_empty_by_default():
    assert prefetch_session_facts() == []


def test_prefetch_instincts_short_input():
    assert prefetch_instincts(["read_file"]) == []


def test_prefetch_instincts_matches(tmp_path, monkeypatch):
    import xavani_memory.instincts as inst
    from xavani_memory.instincts import InstinctRegistry

    path = tmp_path / "instincts.json"
    registry = InstinctRegistry(path=path)
    for sid in ("s1", "s2"):
        registry.record_episode(sid, ["read_file", "patch"])

    monkeypatch.setattr(inst, "_instincts_path", lambda: path)
    from agent import context_prefetch as cp

    matches = cp.prefetch_instincts(["read_file", "patch", "run_tests"])
    assert matches and matches[0]["pattern"] == "read_file->patch"


# ── composed context ────────────────────────────────────────────────


def test_build_prefetch_context_composes(git_repo, tmp_path, monkeypatch):
    import xavani_memory.instincts as inst
    from xavani_memory.instincts import InstinctRegistry

    path = tmp_path / "instincts.json"
    registry = InstinctRegistry(path=path)
    for sid in ("s1", "s2"):
        registry.record_episode(sid, ["read_file", "patch"])
    monkeypatch.setattr(inst, "_instincts_path", lambda: path)

    ctx = build_prefetch_context(
        cwd=str(git_repo),
        session_id="new-session",
        tool_names=["read_file", "patch"],
    )
    assert ctx["git"]["repo_root"] == str(git_repo)
    assert ctx["instincts"]
    assert ctx["durable_facts"] == []


def test_format_prefetch_block_contains_git(git_repo):
    ctx = build_prefetch_context(cwd=str(git_repo))
    block = format_prefetch_block(ctx)
    assert "Repository context" in block
    assert "branch" in block


def test_format_prefetch_block_empty():
    assert format_prefetch_block({}) == ""
    assert format_prefetch_block({"git": {}, "durable_facts": [], "instincts": []}) == ""


def test_format_prefetch_block_includes_facts_and_instincts():
    block = format_prefetch_block({
        "git": {},
        "durable_facts": [{"fact": "I use VS Code.", "confidence": 0.9}],
        "instincts": [{"pattern": "a->b", "count": 3}],
    })
    assert "Durable facts" in block
    assert "I use VS Code." in block
    assert "Pattern instincts" in block
    assert "a->b" in block
