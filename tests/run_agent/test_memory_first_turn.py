# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Memory recall into the first turn (backlog E102)."""

from types import SimpleNamespace

from agent.conversation_loop import prefetch_memory_context
from agent.memory_manager import recall_xavani_memory


class _FakeMemory:
    def __init__(self, hits=None, raise_on_search=False):
        self.hits = hits or []
        self.raise_on_search = raise_on_search

    def search(self, query, limit=10):
        if self.raise_on_search:
            raise RuntimeError("store broken")
        return self.hits[:limit]


def _episode(user_input, outcome=""):
    entry = {"user_input": user_input}
    if outcome:
        entry["outcome"] = outcome
    return entry


class TestRecallXavaniMemory:
    def test_formats_hits_as_bullets(self):
        memory = _FakeMemory([
            (_episode("deploy the bot", "succeeded"), 2.0),
            (_episode("fix the api key"), 1.0),
        ])

        text = recall_xavani_memory(memory, "deploy")

        assert "- deploy the bot → succeeded" in text
        assert "- fix the api key" in text

    def test_empty_query_returns_empty(self):
        assert recall_xavani_memory(_FakeMemory([(_episode("x"), 1.0)]), "") == ""

    def test_none_store_returns_empty(self):
        assert recall_xavani_memory(None, "deploy") == ""

    def test_store_failure_returns_empty(self):
        memory = _FakeMemory(raise_on_search=True)

        assert recall_xavani_memory(memory, "deploy") == ""

    def test_non_dict_entries_skipped(self):
        memory = _FakeMemory([("not-a-dict", 1.0), (_episode("real one", "done"), 1.0)])

        text = recall_xavani_memory(memory, "real")

        assert "not-a-dict" not in text
        assert "real one" in text

    def test_char_cap_truncates(self):
        long_text = "x" * 500
        memory = _FakeMemory([(_episode(long_text, "y"), 1.0)])

        text = recall_xavani_memory(memory, "x", max_chars=100)

        assert len(text) <= 100


class TestPrefetchMemoryContext:
    def test_merges_external_and_local_recall(self):
        agent = SimpleNamespace(
            _memory_manager=SimpleNamespace(
                prefetch_all=lambda q: "external context"
            ),
            _xavani_memory=_FakeMemory([(_episode("deploy the bot", "succeeded"), 1.0)]),
        )

        cache = prefetch_memory_context(agent, "deploy")

        assert "external context" in cache
        assert "deploy the bot" in cache

    def test_external_failure_still_returns_local_recall(self):
        agent = SimpleNamespace(
            _memory_manager=SimpleNamespace(
                prefetch_all=lambda q: (_ for _ in ()).throw(RuntimeError("boom"))
            ),
            _xavani_memory=_FakeMemory([(_episode("deploy the bot", "succeeded"), 1.0)]),
        )

        cache = prefetch_memory_context(agent, "deploy")

        assert "deploy the bot" in cache

    def test_no_local_store_returns_external_only(self):
        agent = SimpleNamespace(
            _memory_manager=SimpleNamespace(prefetch_all=lambda q: "external context"),
            _xavani_memory=None,
        )

        cache = prefetch_memory_context(agent, "deploy")

        assert cache == "external context"

    def test_nothing_configured_returns_empty(self):
        agent = SimpleNamespace(_memory_manager=None, _xavani_memory=None)

        assert prefetch_memory_context(agent, "deploy") == ""
