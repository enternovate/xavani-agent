# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for xavani_cli/magic_keywords.py."""

from xavani_cli.magic_keywords import apply_magic_keywords, detect_magic_keywords


def test_detects_bare_keyword():
    assert detect_magic_keywords("ultrathink solve this puzzle") == ["ultrathink"]


def test_ignores_code_spans_and_blocks():
    assert detect_magic_keywords("use `ultrathink` as a flag") == []
    assert detect_magic_keywords("```\nultrathink\n```") == []


def test_ignores_tags_and_paths():
    assert detect_magic_keywords("<ultrathink>tag</ultrathink>") == []
    assert detect_magic_keywords("run scripts/ultrathink.sh first") == []


def test_detects_multiple_in_canonical_order():
    text = "workflowz this and ultrathink the plan, then orchestrate"
    assert detect_magic_keywords(text) == [
        "ultrathink", "orchestrate", "workflowz",
    ]


def test_apply_appends_directives_and_removes_keyword():
    augmented, detected = apply_magic_keywords("ultrathink prove the lemma")
    assert detected == ["ultrathink"]
    assert "ultrathink" not in augmented.split("\n\n")[0]
    assert "[system note:" in augmented
    assert "step by step" in augmented


def test_apply_without_keywords_is_identity():
    text = "plain question about the buffalo migration"
    augmented, detected = apply_magic_keywords(text)
    assert augmented == text
    assert detected == []
