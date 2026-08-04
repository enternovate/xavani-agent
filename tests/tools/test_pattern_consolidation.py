# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G02: pattern consolidation tests."""

import pytest

from tools.pattern_consolidation import consolidate_patterns


# ── prefix merging ─────────────────────────────────────────────────


def test_prefix_merged_into_longer():
    chains = [
        ("read_file,terminal", 5),
        ("read_file,terminal,patch", 3),
    ]
    report = consolidate_patterns(chains)
    assert report["merged_count"] == 1
    assert report["merged_into"]["read_file,terminal"] == "read_file,terminal,patch"
    # Frequency combined on the longer chain.
    consolidated = dict(report["consolidated"])
    assert consolidated["read_file,terminal,patch"] == 8


def test_no_merge_for_distinct_chains():
    chains = [
        ("read_file,terminal", 4),
        ("web_search,web_extract", 4),
    ]
    report = consolidate_patterns(chains)
    assert report["merged_count"] == 0
    assert len(report["consolidated"]) == 2


def test_exact_duplicates_aggregated():
    chains = [
        ("read_file,terminal", 3),
        ("read_file,terminal", 4),
    ]
    report = consolidate_patterns(chains)
    assert len(report["consolidated"]) == 1
    assert report["consolidated"][0] == ("read_file,terminal", 7)


def test_chain_order_preserved_in_prefix():
    # "terminal,read_file" is NOT a prefix of "read_file,terminal,patch".
    chains = [
        ("terminal,read_file", 5),
        ("read_file,terminal,patch", 3),
    ]
    report = consolidate_patterns(chains)
    assert report["merged_count"] == 0


def test_oversized_chain_dropped():
    chains = [("a,b,c,d,e,f,g,h,i,j", 9)]  # 10 steps > max 8
    report = consolidate_patterns(chains)
    assert report["consolidated"] == []


def test_empty_chain_dropped():
    chains = [("", 5), ("  ,  ", 3)]
    report = consolidate_patterns(chains)
    assert report["consolidated"] == []


def test_chain_with_spaces_normalized():
    chains = [(" read_file , terminal ", 2)]
    report = consolidate_patterns(chains)
    assert report["consolidated"][0][0] == "read_file,terminal"


def test_sorted_by_frequency_desc():
    chains = [("low", 1), ("high", 9)]
    report = consolidate_patterns(chains)
    assert report["consolidated"][0] == ("high", 9)


def test_empty_input():
    report = consolidate_patterns([])
    assert report["consolidated"] == []
    assert report["merged_count"] == 0


def test_multiple_prefix_merges():
    chains = [
        ("a,b", 2),
        ("a,b,c", 4),
        ("a,b,c,d", 1),
    ]
    report = consolidate_patterns(chains)
    assert report["merged_count"] == 2
    assert dict(report["consolidated"])["a,b,c,d"] == 7
