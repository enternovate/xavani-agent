"""Tests for dangerous command-chain detection (D05) and risk tiers (D01)."""

import pytest

from tools.approval import (
    classify_command_risk,
    detect_dangerous_chain,
    split_command_segments,
)

pytestmark = pytest.mark.unit


class TestClassifyCommandRisk:
    def test_safe_command(self):
        assert classify_command_risk("ls -la") == "safe"

    def test_warn_command(self):
        # chmod -R 777 is recoverable-but-costly → warn tier
        assert classify_command_risk("chmod -R 777 /some/dir") == "warn"

    def test_block_command(self):
        assert classify_command_risk("rm -rf /") == "block"

    def test_block_wins_over_warn(self):
        # rm -rf is a hardline (block) even when another warn pattern matches
        assert classify_command_risk("rm -rf / && kill 1") == "block"


class TestSplitCommandSegments:
    def test_splits_on_operators(self):
        segments = split_command_segments("rm -rf a && rm -rf b")
        assert len(segments) == 2

    def test_single_segment(self):
        assert split_command_segments("ls") == ["ls"]

    def test_semicolon_and_pipe(self):
        segments = split_command_segments("cmd1; cmd2 | cmd3")
        assert len(segments) == 3

    def test_quoted_separator_not_split(self):
        segments = split_command_segments("echo 'a && b'")
        assert len(segments) == 1


class TestDetectDangerousChain:
    def test_detects_double_rm_chain(self):
        verdict, hits, description = detect_dangerous_chain("rm -rf /tmp/a && rm -rf /tmp/b")
        assert verdict is True
        assert len(hits) == 2
        assert "chain" in description

    def test_detects_reset_then_force_push(self):
        verdict, hits, _ = detect_dangerous_chain("git reset --hard HEAD && git push --force origin main")
        assert verdict is True
        assert len(hits) >= 2

    def test_single_dangerous_command_not_chain(self):
        verdict, hits, _ = detect_dangerous_chain("rm -rf /tmp/a")
        assert verdict is False
        assert hits == []

    def test_one_dangerous_one_safe(self):
        verdict, _, _ = detect_dangerous_chain("echo hi && rm -rf /tmp/x")
        assert verdict is False

    def test_safe_chain(self):
        verdict, _, _ = detect_dangerous_chain("ls && pwd")
        assert verdict is False

    def test_empty_command(self):
        verdict, _, _ = detect_dangerous_chain("")
        assert verdict is False

    def test_chain_with_semicolons(self):
        verdict, hits, _ = detect_dangerous_chain("rm -rf a; rm -rf b; rm -rf c")
        assert verdict is True
        assert len(hits) == 3
