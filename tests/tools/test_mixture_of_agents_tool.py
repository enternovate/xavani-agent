# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for tools.mixture_of_agents_tool.

The MOA tool is synchronous (ThreadPoolExecutor-based) and provider-agnostic —
it calls create_client() per reference model, then synthesizes with an
aggregator. These tests assert the contract that the production code actually
implements, not an aspirational async/OpenRouter-only rewrite.

Note: ``tools.mixture_of_agents_tool`` imports ``agent.model_client`` lazily
inside the function body, so mocks must be installed via ``sys.modules``
patching, not attribute patching on the tool module.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

moa = importlib.import_module("tools.mixture_of_agents_tool")


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def test_moa_defaults_are_well_formed():
    # Invariants: REFERENCE_MODELS exists, is non-empty, and every entry is a
    # usable model slug for create_client().
    assert isinstance(moa.REFERENCE_MODELS, list)
    assert len(moa.REFERENCE_MODELS) >= 1
    for m in moa.REFERENCE_MODELS:
        assert isinstance(m, str) and len(m) > 0 and not m.startswith("/")
    assert isinstance(moa.DEFAULT_AGGREGATOR_MODEL, str)
    assert len(moa.DEFAULT_AGGREGATOR_MODEL) > 0


# ---------------------------------------------------------------------------
# Retry / warning hygiene — warn on intermediate failures, err on terminal
# ---------------------------------------------------------------------------

def test_call_model_returns_error_dict_on_provider_failure():
    """_call_model returns ok=False with the exception text — never raises."""
    fake_module = MagicMock()
    fake_module.create_client.side_effect = RuntimeError("provider down")
    with patch.dict(sys.modules, {"agent.model_client": fake_module}):
        result = moa._call_model("gpt-4o-mini", "hello")
    assert result["ok"] is False
    assert result["model"] == "gpt-4o-mini"
    assert "provider down" in result["error"]


def test_call_model_returns_response_on_success():
    """_call_model returns ok=True with the model's content."""
    fake_client = MagicMock()
    fake_client.chat.return_value = {"content": "world"}
    fake_module = MagicMock()
    fake_module.create_client.return_value = fake_client
    with patch.dict(sys.modules, {"agent.model_client": fake_module}):
        result = moa._call_model(
            "gpt-4o-mini", "hello", provider="openai", api_key="sk-x"
        )
    assert result["ok"] is True
    assert result["model"] == "gpt-4o-mini"
    assert result["response"] == "world"
    fake_module.create_client.assert_called_once_with(
        model="gpt-4o-mini", provider="openai", base_url=None, api_key="sk-x"
    )


# ---------------------------------------------------------------------------
# Top-level error path
# ---------------------------------------------------------------------------

def test_mixture_of_agents_all_reference_models_fail():
    """When every reference model fails, the pipeline returns ok=False."""
    def failing_call(*args, **kwargs):
        return {"model": args[0], "response": "", "ok": False, "error": "timeout"}

    with patch.object(moa, "_call_model", side_effect=failing_call):
        result = moa.mixture_of_agents(
            "q",
            reference_models=["m1", "m2", "m3"],
            aggregator_model="gpt-4o",
        )
    assert result["ok"] is False
    assert "All reference models failed" in result["error"]
    assert len(result["rounds"]) == 1


def test_mixture_of_agents_succeeds_with_failed_and_passed_refs():
    """Pipeline tolerates partial failure: 2 fails + 1 success still aggregates."""

    remaining_failures = {"m1": 1, "m2": 1}

    def selective_call(model, *args, **kwargs):
        if remaining_failures.get(model, 0) > 0:
            remaining_failures[model] -= 1
            return {"model": model, "response": "", "ok": False, "error": "flake"}
        return {"model": model, "response": f"answer-{model}", "ok": True}

    with patch.object(moa, "_call_model", side_effect=selective_call):
        result = moa.mixture_of_agents(
            "q",
            reference_models=["m1", "m2", "m3"],
            aggregator_model="m3",
        )
    assert result["ok"] is True
    assert "Synthesis error" not in result["answer"]
    # The final aggregation also went through _call_model; the "m3" entry
    # was used once as reference (succeeded on first try) and once as
    # aggregator (succeeded), so both rounds show response fields.
    assert result["aggregator_model"] == "m3"
