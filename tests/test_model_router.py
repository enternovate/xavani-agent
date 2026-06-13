# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the intelligent model router (v1.0.0 major ③).

Verifies: providers are detected from env keys; the best critical-thinker is
chosen for judgment tasks; cheap/fast models win quick/bulk tasks; required
strengths (vision) are enforced; no keys → no choice; routing is deterministic;
and the module makes ZERO API calls (static AST check).
"""

from __future__ import annotations

import ast
from pathlib import Path

import model_router as mr

REPO = Path(__file__).resolve().parents[1]


def test_available_providers_detects_keys() -> None:
    assert mr.available_providers({"ANTHROPIC_API_KEY": "x"}) == {"anthropic"}
    assert mr.available_providers({"GEMINI_API_KEY": "x"}) == {"google"}  # alias
    assert mr.available_providers({}) == set()


def test_judgment_picks_best_critical_thinker() -> None:
    # Emails / advice == judgment. With Anthropic available, the frontier opus wins.
    assert mr.route("judgment", env={"ANTHROPIC_API_KEY": "x"}) == "claude-opus-4-8"
    # With only OpenAI, the frontier OpenAI model wins.
    assert mr.route("judgment", env={"OPENAI_API_KEY": "x"}) == "gpt-5"
    # With both, opus edges gpt-5 on judgment (writing strength).
    both = mr.route("judgment", env={"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x"})
    assert both == "claude-opus-4-8"


def test_quick_prefers_cheap_fast_model() -> None:
    pick = mr.route("quick", env={"ANTHROPIC_API_KEY": "x"})
    assert pick == "claude-haiku-4-5"  # the cheap/fast Anthropic tier


def test_vision_requires_vision_strength() -> None:
    # OpenAI models in the map have no vision strength → no eligible model.
    assert mr.route("vision", env={"OPENAI_API_KEY": "x"}) is None
    # Google has vision models; the stronger one wins.
    assert mr.route("vision", env={"GOOGLE_API_KEY": "x"}) == "gemini-2.5-pro"


def test_no_provider_returns_none() -> None:
    assert mr.route("judgment", env={}) is None
    assert "set a provider API key" in mr.explain("judgment", env={})


def test_route_is_deterministic() -> None:
    env = {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x", "DEEPSEEK_API_KEY": "x"}
    a = [mr.route(tc, env=env) for tc in ("judgment", "code", "quick", "bulk", "long_context")]
    b = [mr.route(tc, env=env) for tc in ("judgment", "code", "quick", "bulk", "long_context")]
    assert a == b


def test_unknown_task_class_falls_back() -> None:
    # An unseen task class should not crash — it falls back to the default ranking.
    assert mr.route("nonsense-task", env={"ANTHROPIC_API_KEY": "x"}) == "claude-opus-4-8"


def test_explain_is_readable() -> None:
    text = mr.explain("judgment", env={"ANTHROPIC_API_KEY": "x"})
    assert "claude-opus-4-8" in text and "judgment" in text


# --------------------------------------------------------------------------- #
# R10 — the router makes ZERO API calls (static AST check)
# --------------------------------------------------------------------------- #
_FORBIDDEN_ROOTS = {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq", "together", "requests", "httpx"}
_FORBIDDEN_SUBSTRINGS = ("openrouter_client", "xai_http", "generativeai")


def test_router_is_zero_llm() -> None:
    path = REPO / "model_router.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    for module in mods:
        root = module.split(".")[0]
        assert root not in _FORBIDDEN_ROOTS, f"model_router imports '{module}' — must stay zero-LLM (R10)"
        assert not any(s in module for s in _FORBIDDEN_SUBSTRINGS), f"model_router imports '{module}' (R10)"
