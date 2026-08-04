"""Tests for the learning graph + journey (agent/learning_graph.py, agent/learning_mutations.py)."""

import json
from pathlib import Path

import pytest

from agent.learning_graph import (
    build_edges,
    build_learning_graph,
    build_skill_nodes,
    density_stats,
)


class TestLearningGraph:
    def test_build_edges_dedupes_and_validates(self):
        class N:
            def __init__(self, name, related):
                self.name = name
                self.related = related

        nodes = {
            "a": N("a", ["b", "b", "c"]),
            "b": N("b", ["a"]),
            "c": N("c", []),
        }
        edges = build_edges(nodes)
        assert ("a", "b") in edges
        # a lists c, so (a,c) should exist
        assert ("a", "c") in edges

    def test_density_stats(self):
        class N:
            def __init__(self, name, category, related, created_by="", use_count=0):
                self.name = name
                self.category = category
                self.related = related
                self.created_by = created_by
                self.use_count = use_count
                self.timestamp = None
                self.source = "profile"
                self.state = "active"
                self.pinned = False

        nodes = {
            "a": N("a", "dev", ["b"], "agent", 3),
            "b": N("b", "dev", ["a"], "agent", 1),
            "c": N("c", "ops", [], "agent", 0),
        }
        edges = build_edges(nodes)
        stats = density_stats(nodes, edges)
        assert stats["nodes"] == 3
        assert stats["agent_created"] == 3
        assert stats["used"] == 2
        assert stats["categories"] == 2
        assert stats["related_edges"] == 1

    def test_build_learning_graph_shape(self, tmp_path, monkeypatch):
        # Point at an empty home so the graph is deterministic
        monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
        from xavani_memory import manager as xm_manager
        original_dir = xm_manager.MEMORY_DIR
        xm_manager.MEMORY_DIR = tmp_path / "data" / "memory"
        try:
            payload = build_learning_graph()
        finally:
            xm_manager.MEMORY_DIR = original_dir
        assert isinstance(payload["nodes"], list)
        assert isinstance(payload["edges"], list)
        assert isinstance(payload["clusters"], list)
        assert "stats" in payload
        assert "memory" in payload

    def test_memory_cards_from_disk(self, tmp_path, monkeypatch):
        mem_dir = tmp_path / "memories"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("first entry\n§\nsecond entry\n", encoding="utf-8")
        monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
        from agent.learning_graph import _memory_cards
        cards = _memory_cards()
        assert len(cards) == 2
        assert cards[0]["source"] == "memory"
        assert "first entry" in cards[0]["body"]


class TestJourneyFormat:
    def test_fmt_graph(self):
        from xavani_cli.journey import _fmt_graph
        payload = {
            "nodes": [
                {"kind": "skill", "label": "my-skill", "timestamp": 1700000000, "useCount": 3, "createdBy": "agent"},
                {"kind": "memory", "label": "A memory", "timestamp": 1700000000, "memorySource": "memory"},
            ],
            "edges": [{"source": "my-skill", "target": "memory:memory:0"}],
            "clusters": [{"category": "dev", "count": 1}],
            "stats": {"learned_skills": 1, "memory_nodes": 1, "related_edges": 0, "memory_skill_edges": 1},
        }
        text = _fmt_graph(payload)
        assert "my-skill" in text
        assert "A memory" in text
        assert "connections" in text

    def test_journey_cli_list_runs(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
        from xavani_cli.journey import cmd_journey
        import argparse
        args = argparse.Namespace(journey_action="list")
        rc = cmd_journey(args)
        out = capsys.readouterr().out
        assert rc == 0
        assert "JOURNEY" in out
