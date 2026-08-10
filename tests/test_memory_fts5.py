# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S3-5 (E101): FTS5 memory search backend on ``MemoryManager.search``.

Covers: distinctive-term matching, relevance ordering (exact match above
partial), empty-query safety, and the substring-scan fallback when FTS5
is unavailable. All offline — no network.
"""

from __future__ import annotations

import pytest

import xavani_memory.manager as manager_mod
from xavani_memory.manager import MemoryManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_MEMORY_FTS5", "1")
    m = MemoryManager(memory_dir=tmp_path / "memory", auto_maintenance=False)
    m.set_session("test-session")
    yield m
    try:
        m.stop_maintenance()
    except Exception:
        pass


def _seed(manager, text, *, response=None, outcome=None):
    manager.remember(
        user_input=text,
        agent_response=response or "ok",
        outcome=outcome,
    )


def test_search_returns_matches_for_distinctive_term(manager):
    _seed(manager, "debugged the postgres connection timeout")
    _seed(manager, "refactored the invoice pipeline")
    _seed(manager, "the kangaroo hopped across the outback")

    results = manager.search("kangaroo", limit=10)
    assert results
    texts = [entry["user_input"] for entry, _ in results]
    assert any("kangaroo" in t for t in texts)


def test_search_ranks_exact_match_above_partial(manager):
    _seed(manager, "kangaroo migration patterns in australia", response="study notes")
    _seed(manager, "the zoo newsletter mentioned kangaroo in passing", response="noise")

    results = manager.search("kangaroo migration", limit=10)
    assert len(results) >= 2
    top_entry, top_score = results[0]
    _, lower_score = results[1]
    assert "migration" in top_entry["user_input"]
    assert top_score > lower_score


def test_search_empty_query_returns_nothing(manager):
    _seed(manager, "anything at all")
    assert manager.search("") == []
    assert manager.search("   ") == []


def test_search_falls_back_to_substring_scan(manager, monkeypatch):
    monkeypatch.setattr(manager_mod, "_fts5_supported", lambda: False)
    _seed(manager, "the walrus and the carpenter")
    _seed(manager, "unrelated entry")

    results = manager.search("walrus", limit=10)
    assert results
    texts = [entry["user_input"] for entry, _ in results]
    assert any("walrus" in t for t in texts)


def test_search_substring_scores_more_fields_higher(manager, monkeypatch):
    monkeypatch.setattr(manager_mod, "_fts5_supported", lambda: False)
    _seed(manager, "quokka facts", response="quokka care guide", outcome="done")
    _seed(manager, "quokka mentioned once", response="ok")

    results = manager.search("quokka", limit=10)
    assert len(results) >= 2
    top_entry, top_score = results[0]
    _, lower_score = results[1]
    assert "facts" in top_entry["user_input"]
    assert top_score > lower_score
