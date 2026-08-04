# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C15: statusline API tests."""

from xavani_cli.statusline import (
    build_statusline_segments,
    context_tier_for,
    render_statusline,
)


def test_empty_state_produces_placeholder():
    segments = build_statusline_segments(None)
    assert segments  # model placeholder
    assert segments[0][0] == "?"
    assert segments[0][1] == "strong"


def test_model_and_provider():
    segments = build_statusline_segments(
        {"model": "claude-opus", "provider": "anthropic"}
    )
    assert segments[0][0] == "claude-opus (anthropic)"


def test_context_usage_low_tier():
    segments = build_statusline_segments(
        {"context_used": 10_000, "context_budget": 200_000}
    )
    ctx = [s for s in segments if s[0].startswith("ctx ")]
    assert len(ctx) == 1
    assert ctx[0][1] == "default"  # 5% usage


def test_context_usage_warn_tier():
    assert context_tier_for(0.9) == "warn"
    assert context_tier_for(0.7) == "good"
    assert context_tier_for(0.1) == "default"


def test_turn_and_background():
    segments = build_statusline_segments(
        {"turn": 3, "background_tasks": 2}
    )
    texts = [s[0] for s in segments]
    assert "turn 3" in texts
    assert "2 bg" in texts


def test_session_shortened():
    segments = build_statusline_segments(
        {"session_id": "20260804_123456_abcdef12"}
    )
    assert any(s[0] == "abcdef12" for s in segments)


def test_render_plain_text():
    segments = build_statusline_segments(
        {"model": "m1", "context_used": 1000, "context_budget": 200_000}
    )
    rendered = render_statusline(segments)
    assert "m1" in rendered
    assert "ctx" in rendered
    assert "│" in rendered


def test_render_empty():
    assert render_statusline([]) == ""


def test_missing_budget_defaults():
    segments = build_statusline_segments({"context_used": 100_000})
    ctx = [s for s in segments if s[0].startswith("ctx ")]
    assert len(ctx) == 1  # uses the default budget, no crash


def test_token_formatting():
    segments = build_statusline_segments(
        {"context_used": 1_500_000, "context_budget": 2_000_000}
    )
    ctx = [s for s in segments if s[0].startswith("ctx ")][0]
    assert "1.5M" in ctx[0]
    assert "2.0M" in ctx[0]
