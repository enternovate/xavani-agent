# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B01: instinct registry — pattern-completion engine tests."""

import pytest

import xavani_memory.instincts as inst
from xavani_memory.instincts import (
    InstinctRegistry,
    format_instinct_hint,
)


@pytest.fixture
def registry(tmp_path):
    return InstinctRegistry(path=tmp_path / "instincts.json")


# ── recording ───────────────────────────────────────────────────────


def test_record_single_episode_no_pattern(registry):
    """One episode is evidence, not yet a pattern."""
    registry.record_episode("s1", ["read_file", "write_file"])
    assert registry.pattern_count() == 1  # the chain is stored...
    assert registry.strongest()[0]["count"] == 1


def test_record_repeated_chain_increments(registry):
    for sid in ("s1", "s2", "s3"):
        registry.record_episode(sid, ["read_file", "patch", "run_tests"])
    strongest = registry.strongest()
    assert strongest
    assert strongest[0]["count"] == 3
    assert "read_file->patch->run_tests" == strongest[0]["pattern"]


def test_clock_tie_prefers_longer_chain(registry, monkeypatch):
    """When last_seen ties (same clock tick), the longer chain must rank first.

    Regression: under load, consecutive time.time() calls collapse to one
    tick; Python's stable sort then kept insertion order, ranking the
    short subchain 'patch->run_tests' above the full chain it came from.
    """
    monkeypatch.setattr("xavani_memory.instincts.time.time", lambda: 1000.0)
    for sid in ("s1", "s2", "s3"):
        registry.record_episode(sid, ["read_file", "patch", "run_tests"])
    strongest = registry.strongest()
    assert strongest[0]["pattern"] == "read_file->patch->run_tests"


def test_record_short_chain_ignored(registry):
    registry.record_episode("s1", ["read_file"])
    assert registry.pattern_count() == 0


def test_record_stores_all_subchains(registry):
    registry.record_episode("s1", ["a", "b", "c"])
    # Length-2 and length-3 chains.
    keys = {p["pattern"] for p in registry.strongest(limit=10)}
    assert "a->b" in keys
    assert "b->c" in keys
    assert "a->b->c" in keys


def test_record_tracks_sessions(registry):
    registry.record_episode("s1", ["a", "b"])
    registry.record_episode("s2", ["a", "b"])
    matches = registry.match(["a", "b"])
    assert matches[0]["sessions"] == ["s1", "s2"]


# ── matching ────────────────────────────────────────────────────────


def test_match_finds_contiguous_chain(registry):
    registry.record_episode("s1", ["read_file", "patch"])
    matches = registry.match(["read_file", "patch", "run_tests"])
    assert matches and matches[0]["pattern"] == "read_file->patch"


def test_match_ignores_non_contiguous(registry):
    registry.record_episode("s1", ["read_file", "patch"])
    # Same tools, different order — not a match.
    assert registry.match(["patch", "read_file"]) == []


def test_match_requires_min_length(registry):
    registry.record_episode("s1", ["a", "b"])
    assert registry.match(["a"]) == []


def test_match_confidence_scales_with_count(registry):
    for sid in ("s1", "s2", "s3", "s4", "s5"):
        registry.record_episode(sid, ["a", "b"])
    matches = registry.match(["a", "b"])
    assert matches[0]["confidence"] == 0.5  # 5/10 cap


def test_match_limit(registry):
    for sid in ("s1", "s2", "s3"):
        registry.record_episode(sid, ["a", "b"])
        registry.record_episode(sid, ["c", "d"])
    assert len(registry.match(["a", "b", "c", "d"], limit=1)) == 1


def test_empty_match(registry):
    assert registry.match([]) == []
    assert registry.match(["x"]) == []


# ── persistence ─────────────────────────────────────────────────────


def test_registry_persists_across_instances(tmp_path):
    path = tmp_path / "instincts.json"
    r1 = InstinctRegistry(path=path)
    r1.record_episode("s1", ["a", "b"])
    r1.record_episode("s2", ["a", "b"])
    r2 = InstinctRegistry(path=path)
    matches = r2.match(["a", "b"])
    assert matches and matches[0]["count"] == 2


def test_corrupt_file_loads_empty(tmp_path):
    path = tmp_path / "instincts.json"
    path.write_text("{not json", encoding="utf-8")
    r = InstinctRegistry(path=path)
    assert r.pattern_count() == 0


def test_clear(registry):
    registry.record_episode("s1", ["a", "b"])
    registry.clear()
    assert registry.pattern_count() == 0


def test_storage_bound_trimmed(tmp_path):
    path = tmp_path / "instincts.json"
    r = InstinctRegistry(path=path)
    for i in range(60):
        r.record_episode(f"s{i}", [f"t{i}", f"t{i + 1}"])
    assert r.pattern_count() <= inst.MAX_PATTERNS


# ── hint formatting ─────────────────────────────────────────────────


def test_format_instinct_hint():
    block = format_instinct_hint([
        {"pattern": "read_file->patch", "count": 3, "confidence": 0.3},
    ])
    assert "Pattern instincts" in block
    assert "read_file->patch" in block
    assert "3x" in block


def test_format_instinct_hint_empty():
    assert format_instinct_hint([]) == ""
