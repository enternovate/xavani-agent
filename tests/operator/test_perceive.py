# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for deterministic perception collectors (v0.7.0 operator U9–U14)."""

from __future__ import annotations

import os
import subprocess

from xavani_operator.config import Channel, ProductConfig, ProductInfo
from xavani_operator.perceive import (
    collect_channel_signals,
    collect_issue_signals,
    collect_last_cycle,
    collect_metrics_signals,
    collect_repo_signals,
    collect_test_signals,
    perceive,
    perception_changed,
)
from xavani_operator.state import OperatorState
from xavani_operator.types import Perception

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(repo, *args):
    subprocess.run(
        ["git", *args], cwd=str(repo), check=True, capture_output=True, text=True, env=_GIT_ENV
    )


def _init_repo(repo):
    _git(repo, "init", "-b", "main")


def _commit_all(repo, msg):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)


# --- U9: repo signals -------------------------------------------------------

def test_repo_signals_report_non_git(tmp_path):
    assert collect_repo_signals(tmp_path)["is_git"] is False


def test_repo_signals_clean_repo(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("hi")
    _commit_all(tmp_path, "first commit")
    sig = collect_repo_signals(tmp_path)
    assert sig["is_git"] is True
    assert sig["branch"] == "main"
    assert sig["dirty"] is False
    assert "first commit" in sig["recent_commits"]


def test_repo_signals_dirty_repo(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("hi")
    _commit_all(tmp_path, "first")
    (tmp_path / "b.txt").write_text("uncommitted")  # untracked -> dirty
    sig = collect_repo_signals(tmp_path)
    assert sig["dirty"] is True
    assert sig["dirty_files"] >= 1


# --- U10: test signals ------------------------------------------------------

def test_test_signals_unknown_without_cache(tmp_path):
    assert collect_test_signals(tmp_path)["known"] is False


def test_test_signals_read_pytest_lastfailed(tmp_path):
    cache = tmp_path / ".pytest_cache" / "v" / "cache"
    cache.mkdir(parents=True)
    (cache / "lastfailed").write_text(
        '{"tests/test_a.py::test_x": true, "tests/test_b.py::test_y": true}'
    )
    sig = collect_test_signals(tmp_path)
    assert sig["known"] is True
    assert sig["failing"] == 2


# --- U11: issue signals -----------------------------------------------------

def test_issue_signals_find_todo_and_fixme(tmp_path):
    (tmp_path / "mod.py").write_text("x = 1  # TODO: fix this\n# FIXME: later\n")
    issues = collect_issue_signals(tmp_path)
    markers = {i["marker"] for i in issues}
    assert "TODO" in markers
    assert "FIXME" in markers


def test_issue_signals_skip_vcs_and_caches(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hooks.py").write_text("# TODO: ignore me\n")
    (tmp_path / "real.py").write_text("# TODO: count me\n")
    issues = collect_issue_signals(tmp_path)
    files = {i["file"] for i in issues}
    assert any("real.py" in f for f in files)
    assert not any(".git" in f for f in files)


# --- U12: channel signals ---------------------------------------------------

def test_channel_signals_project_configured_channels():
    chans = [Channel(platform="x", handle="@a"), Channel(platform="discord")]
    sig = collect_channel_signals(chans)
    assert set(sig) == {"x", "discord"}
    assert sig["x"]["handle"] == "@a"
    assert sig["x"]["unread"] is None  # no live data without a provider


def test_channel_signals_use_inbox_provider():
    chans = [Channel(platform="x", handle="@a")]
    sig = collect_channel_signals(chans, inbox_provider=lambda platform, handle: 3)
    assert sig["x"]["unread"] == 3


# --- U13: metrics + last cycle ---------------------------------------------

def test_last_cycle_none_when_empty(tmp_path):
    assert collect_last_cycle(OperatorState(root=tmp_path)) is None


def test_last_cycle_returns_most_recent(tmp_path):
    st = OperatorState(root=tmp_path)
    st.put("cycles", "c1", {"cycle_id": "c1", "created_at": 1.0})
    st.put("cycles", "c2", {"cycle_id": "c2", "created_at": 2.0})
    assert collect_last_cycle(st)["cycle_id"] == "c2"


def test_metrics_reads_json(tmp_path):
    p = tmp_path / "metrics.json"
    p.write_text('{"signups": 10}')
    assert collect_metrics_signals(p)["signups"] == 10


def test_metrics_empty_without_file():
    assert collect_metrics_signals(None) == {}


# --- U14: assembly + content hash ------------------------------------------

def test_perceive_assembles_sections(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.py").write_text("# TODO: x\n")
    _commit_all(tmp_path, "init")
    cfg = ProductConfig(product=ProductInfo(name="X", repo=str(tmp_path)))
    p = perceive(cfg)
    assert isinstance(p, Perception)
    assert p.repo["is_git"] is True
    assert any(i["marker"] == "TODO" for i in p.issues)
    assert p.content_hash


def test_perceive_hash_is_stable_for_same_state(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    _commit_all(tmp_path, "init")
    cfg = ProductConfig(product=ProductInfo(name="X", repo=str(tmp_path)))
    assert perceive(cfg).content_hash == perceive(cfg).content_hash


def test_perception_changed_compares_hash(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.py").write_text("x = 1\n")
    _commit_all(tmp_path, "init")
    cfg = ProductConfig(product=ProductInfo(name="X", repo=str(tmp_path)))
    p = perceive(cfg)
    assert perception_changed(p, None) is True
    assert perception_changed(p, p.content_hash) is False
