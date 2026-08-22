# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/conflict_resolver.py."""

import pytest

from xavani_cli.conflict_resolver import (
    count_conflicts,
    parse_conflicts,
    resolve_conflicts,
)

SIMPLE = """header line
<<<<<<< HEAD
ours line one
ours line two
=======
theirs line one
>>>>>>> feature
tail line
"""

DIFF3 = """<<<<<<< HEAD
ours kept
||||||| merged common ancestors
base text
=======
theirs won
>>>>>>> other
"""


def test_parse_counts_and_sides():
    conflicts = parse_conflicts(SIMPLE)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["index"] == 1
    assert c["ours"] == "ours line one\nours line two\n"
    assert c["theirs"] == "theirs line one\n"


def test_parse_diff3_base_section():
    conflicts = parse_conflicts(DIFF3)
    assert len(conflicts) == 1
    assert conflicts[0]["base"] == "base text\n"
    assert conflicts[0]["ours"] == "ours kept\n"
    assert conflicts[0]["theirs"] == "theirs won\n"


def test_resolve_ours_keeps_ours_side():
    out = resolve_conflicts(SIMPLE, "ours")
    assert "ours line one" in out
    assert "theirs line one" not in out
    assert "<<<<<<<" not in out
    assert out.startswith("header line\n")
    assert out.endswith("tail line\n")


def test_resolve_theirs_keeps_theirs_side():
    out = resolve_conflicts(SIMPLE, "theirs")
    assert "theirs line one" in out
    assert "ours line one" not in out


def test_resolve_base_uses_diff3_section():
    out = resolve_conflicts(DIFF3, "base")
    assert "base text" in out
    assert "ours kept" not in out


def test_resolve_base_falls_back_to_ours_when_absent():
    out = resolve_conflicts(SIMPLE, "base")
    assert "ours line one" in out


def test_resolve_multiple_blocks():
    two = SIMPLE + "\nmiddle\n\n" + DIFF3
    assert count_conflicts(two) == 2
    out = resolve_conflicts(two, "theirs")
    assert count_conflicts(out) == 0
    assert "theirs won" in out


def test_unknown_strategy_raises():
    with pytest.raises(ValueError):
        resolve_conflicts(SIMPLE, "random")


def test_clean_file_is_unchanged():
    assert resolve_conflicts("no conflicts here\n", "ours") == (
        "no conflicts here\n"
    )
