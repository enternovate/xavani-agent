# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C09: progressive compaction tests.

progressive_compress() collapses the OLDEST chunks first, one stage at
a time, and stops as soon as the trajectory fits the budget — recent
turns stay untouched as long as possible.
"""

import pytest

from trajectory_compressor import CompressionConfig, TrajectoryCompressor


def _make_turn(role: str, content: str) -> dict:
    # The compressor's format uses "from"/"value" keys.
    return {"from": role, "value": content}


def _make_trajectory(n_turns: int, words_per_turn: int = 30) -> list:
    """System head + n user/assistant pairs with enough tokens each."""
    turns = [_make_turn("system", "You are Xavani, a helpful assistant.")]
    for i in range(n_turns):
        words = " ".join(f"word{j}" for j in range(words_per_turn))
        turns.append(_make_turn("human", f"prompt {i}: {words}"))
        turns.append(_make_turn("gpt", f"answer {i}: {words}"))
    return turns


@pytest.fixture
def compressor():
    """Compressor with a stub tokenizer (no transformers dependency)."""
    from unittest.mock import MagicMock

    config = CompressionConfig()
    config.target_max_tokens = 3000
    config.protect_last_n_turns = 2
    tc = TrajectoryCompressor.__new__(TrajectoryCompressor)
    tc.config = config
    tc.logger = MagicMock()
    tc.tokenizer = MagicMock()
    # Stub: 1 token per ~4 chars, mirroring the built-in fallback.
    tc.tokenizer.encode = MagicMock(side_effect=lambda s: list(range((len(s) or 1) // 4 + 1)))
    return tc


def test_under_target_skipped(compressor):
    traj = _make_trajectory(3)  # small
    result, metrics = compressor.progressive_compress(traj)
    assert metrics.skipped_under_target is True
    assert result == traj


def test_progressive_reduces_to_target(compressor):
    traj = _make_trajectory(30)  # over budget
    result, metrics = compressor.progressive_compress(traj, chunk_turns=4)
    assert metrics.compressed_tokens <= 3000
    assert len(result) < len(traj)


def test_recent_turns_preserved(compressor):
    """The tail (protected recent turns) must appear verbatim."""
    traj = _make_trajectory(30)
    result, _ = compressor.progressive_compress(traj, chunk_turns=4)
    # The last user message survives intact.
    last_user = traj[-2]
    assert last_user in result


def test_summary_markers_present(compressor):
    traj = _make_trajectory(30)
    result, _ = compressor.progressive_compress(traj, chunk_turns=4)
    summaries = [t for t in result if t["from"] == "system" and "compressed" in t["value"]]
    assert summaries


def test_progressive_compresses_less_than_aggressive(compressor):
    """Progressive stops early; aggressive compresses the whole region."""
    traj = _make_trajectory(25)
    progressive_result, _ = compressor.progressive_compress(traj, chunk_turns=6)
    aggressive_result, _ = compressor.compress_trajectory(traj)
    assert len(progressive_result) >= len(aggressive_result)


def test_chunk_size_controls_granularity(compressor):
    traj = _make_trajectory(30)
    _, m_small = compressor.progressive_compress(traj, chunk_turns=2)
    _, m_big = compressor.progressive_compress(traj, chunk_turns=10)
    # Smaller chunks stop earlier -> fewer turns removed -> more kept.
    assert m_small.compressed_turns >= m_big.compressed_turns


def test_summarize_chunk_structure(compressor):
    chunk = [
        _make_turn("human", "hi"),
        _make_turn("gpt", "hello"),
        _make_turn("tool", "result"),
    ]
    summary = compressor._summarize_chunk(chunk)
    assert "compressed 3 turns" in summary
    assert "1 user" in summary
    assert "1 assistant" in summary


def test_empty_region_no_crash(compressor):
    traj = [_make_turn("system", "only system turn")]
    result, metrics = compressor.progressive_compress(traj, chunk_turns=4)
    assert metrics.skipped_under_target or metrics.still_over_limit
    assert isinstance(result, list)
