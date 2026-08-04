# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B02: session summarizer with confidence scoring.

Facts are extracted deterministically with confidence scores, stored
per session, and recalled only above the threshold.
"""

import pytest

import xavani_memory.summarizer as summ
from xavani_memory.summarizer import (
    DEFAULT_MIN_CONFIDENCE,
    extract_facts,
    format_recall_prompt,
    recall_facts,
    store_facts,
)


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    store = tmp_path / "summaries.jsonl"
    monkeypatch.setattr(summ, "_summary_path", lambda: store)
    yield store
    try:
        store.unlink(missing_ok=True)
    except OSError:
        pass


# ── fact extraction ─────────────────────────────────────────────────


def test_preference_statement_high_confidence():
    facts = extract_facts([{"user_input": "I use VS Code for all my work.", "session_id": "s1"}])
    assert facts
    assert facts[0]["confidence"] >= 0.9
    assert "VS Code" in facts[0]["fact"]


def test_negative_statement_medium_confidence():
    facts = extract_facts([{"user_input": "I don't like dark mode themes.", "session_id": "s1"}])
    assert facts
    assert facts[0]["confidence"] == 0.6


def test_repeated_topic_corroborated():
    episodes = [
        {"user_input": "The postgres query is slow.", "session_id": "s1"},
        {"user_input": "Let me check the postgres index.", "session_id": "s1"},
        {"user_input": "postgres vacuum took long.", "session_id": "s1"},
    ]
    facts = extract_facts(episodes)
    postgres_facts = [f for f in facts if "postgres" in f["fact"].lower()]
    assert postgres_facts
    assert postgres_facts[0]["confidence"] >= 0.7


def test_single_mention_not_corroborated():
    facts = extract_facts([{"user_input": "openai rate limits are annoying.", "session_id": "s1"}])
    repeated = [f for f in facts if f["source"].startswith("repeated_mention")]
    assert repeated == []


def test_empty_input_no_facts():
    assert extract_facts([{"user_input": "", "session_id": "s1"}]) == []


def test_facts_sorted_by_confidence():
    episodes = [
        {"user_input": "I prefer ruff for linting.", "session_id": "s1"},  # 0.9
        {"user_input": "I don't like black.", "session_id": "s1"},  # 0.6
    ]
    facts = extract_facts(episodes)
    assert facts[0]["confidence"] >= facts[-1]["confidence"]


# ── storage + recall ────────────────────────────────────────────────


def test_store_and_recall_roundtrip(_isolated_store):
    facts = extract_facts([{"user_input": "I use Rust for CLI tools.", "session_id": "s1"}])
    assert store_facts(facts) is True
    recalled = recall_facts()
    assert recalled
    assert recalled[0]["confidence"] >= DEFAULT_MIN_CONFIDENCE


def test_recall_filters_below_threshold(_isolated_store):
    store_facts([{"fact": "weak fact", "confidence": 0.2, "source": "test", "session_id": "s1"}])
    assert recall_facts() == []


def test_recall_excludes_current_session(_isolated_store):
    store_facts([{"fact": "I use Neovim.", "confidence": 0.9, "source": "preference", "session_id": "current"}])
    assert recall_facts(session_id="current") == []
    assert len(recall_facts(session_id="other")) == 1


def test_recall_limit(_isolated_store):
    for i in range(5):
        store_facts([{"fact": f"fact {i}", "confidence": 0.9, "source": "t", "session_id": f"s{i}"}])
    assert len(recall_facts(limit=2)) == 2


def test_recall_newest_first(_isolated_store):
    store_facts([{"fact": "older", "confidence": 0.9, "source": "t", "session_id": "s1"}])
    store_facts([{"fact": "newer", "confidence": 0.9, "source": "t", "session_id": "s2"}])
    assert recall_facts()[0]["fact"] == "newer"


# ── prompt formatting ───────────────────────────────────────────────


def test_format_recall_prompt():
    block = format_recall_prompt([{"fact": "I use VS Code.", "confidence": 0.9}])
    assert "Recalled durable facts" in block
    assert "I use VS Code." in block
    assert "90%" in block


def test_format_recall_prompt_empty():
    assert format_recall_prompt([]) == ""


# ── MemoryManager integration ───────────────────────────────────────


def test_manager_recall_context_has_durable_facts(tmp_path, monkeypatch):
    store = tmp_path / "summaries.jsonl"
    monkeypatch.setattr(summ, "_summary_path", lambda: store)

    from xavani_memory.manager import MemoryManager

    mm = MemoryManager(memory_dir=tmp_path / "mem")
    mm.new_session()
    # A preference recorded in a PAST session.
    past = MemoryManager(memory_dir=tmp_path / "mem")
    past.new_session()
    past.remember("I use pytest for all tests.")
    # Fresh manager must surface the durable fact in recall context.
    fresh = MemoryManager(memory_dir=tmp_path / "mem")
    fresh.new_session()
    context = fresh.get_recall_context(force=True)
    assert context["durable_facts"]
    assert any("pytest" in f["fact"] for f in context["durable_facts"])
