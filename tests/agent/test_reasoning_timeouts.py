# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B01: per-model-family reasoning-token ceiling tests."""

from __future__ import annotations

from agent.reasoning_timeouts import (
    MAX_REASONING_TOKENS_BY_FAMILY,
    max_reasoning_tokens_for,
)


def test_known_family_returns_ceiling():
    assert max_reasoning_tokens_for("claude-3-5-haiku-20241022") == 8192
    assert max_reasoning_tokens_for("gpt-5") == 32000


def test_longest_match_wins():
    # "gpt-5" also contains "gpt-5-mini"?  No — the reverse: a mini model
    # must match its own row, not the generic one.
    assert max_reasoning_tokens_for("gpt-5-mini") == 8192
    assert max_reasoning_tokens_for("claude-3-5-sonnet-latest") == 16000


def test_unknown_model_has_no_cap():
    assert max_reasoning_tokens_for("llama-3.3-70b") == 0


def test_fallback_respected_for_unknown():
    assert max_reasoning_tokens_for("llama-3.3-70b", fallback=12000) == 12000


def test_empty_model_returns_fallback():
    assert max_reasoning_tokens_for("") == 0
    assert max_reasoning_tokens_for(None, fallback=5) == 5


def test_case_insensitive_match():
    assert max_reasoning_tokens_for("CLAUDE-3-5-SONNET") == 16000


def test_database_is_nonempty():
    assert len(MAX_REASONING_TOKENS_BY_FAMILY) >= 5
