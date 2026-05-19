# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the Nous-Xavani-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"xavani"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``xavani-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "xavani" tag namespace.

``is_nous_xavani_non_agentic`` should only match the actual Nous Research
Xavani-3 / Xavani-4 chat family.
"""

from __future__ import annotations

import pytest

from xavani_cli.model_switch import (
    _XAVANI_MODEL_WARNING,
    _check_xavani_model_warning,
    is_nous_xavani_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Xavani-3-Llama-3.1-70B",
        "NousResearch/Xavani-3-Llama-3.1-405B",
        "xavani-3",
        "Xavani-3",
        "xavani-4",
        "xavani-4-405b",
        "xavani_4_70b",
        "openrouter/xavani3:70b",
        "openrouter/nousresearch/xavani-4-405b",
        "NousResearch/Xavani3",
        "xavani-3.1",
    ],
)
def test_matches_real_nous_xavani_chat_models(model_name: str) -> None:
    assert is_nous_xavani_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Xavani 3/4"
    )
    assert _check_xavani_model_warning(model_name) == _XAVANI_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "xavani-brain:qwen3-14b-ctx16k",
        "xavani-brain:qwen3-14b-ctx32k",
        "xavani-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Xavani models we don't warn about
        "xavani-llm-2",
        "xavani2-pro",
        "nous-xavani-2-mistral",
        # Edge cases
        "",
        "xavani",  # bare "xavani" isn't the 3/4 family
        "xavani-brain",
        "brain-xavani-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_xavani_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Xavani 3/4"
    )
    assert _check_xavani_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_xavani_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_xavani_model_warning("") == ""
