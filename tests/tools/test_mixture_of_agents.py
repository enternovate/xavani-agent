# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Tests for tools/mixture_of_agents_tool.py — MoA pipeline."""

import json
from unittest.mock import patch

import pytest

from tools.mixture_of_agents_tool import (
    mixture_of_agents,
    _handle_mixture_of_agents,
    MIXTURE_OF_AGENTS_SCHEMA,
)

pytestmark = pytest.mark.unit


def _fake_call_model(model, prompt, system="", provider=None, base_url=None, api_key=None, timeout=60):
    """Canned model response for testing."""
    return {
        "model": model,
        "response": f"Response from {model}: the answer is 42",
        "ok": True,
    }


def _failing_call_model(model, prompt, system="", provider=None, base_url=None, api_key=None, timeout=60):
    """Simulates a failing model."""
    return {"model": model, "response": "", "ok": False, "error": "timeout"}


class TestMixtureOfAgents:
    """Test the MoA pipeline."""

    @patch("tools.mixture_of_agents_tool._call_model", side_effect=_fake_call_model)
    def test_single_round_aggregation(self, mock_call):
        """Single round: N reference models + 1 aggregator."""
        result = mixture_of_agents(
            prompt="What is the meaning of life?",
            reference_models=["model-a", "model-b"],
            aggregator_model="aggregator",
        )
        assert result["ok"] is True
        assert "answer" in result
        assert result["total_rounds"] == 1
        # 2 reference + 1 aggregator = 3 calls
        assert mock_call.call_count == 3

    @patch("tools.mixture_of_agents_tool._call_model", side_effect=_fake_call_model)
    def test_multi_round(self, mock_call):
        """Multi-round: feeds aggregator output back."""
        result = mixture_of_agents(
            prompt="complex problem",
            reference_models=["model-a"],
            aggregator_model="aggregator",
            rounds=2,
        )
        assert result["ok"] is True
        assert result["total_rounds"] == 2
        # Round 1: 1 ref + 1 agg = 2; Round 2: 1 ref + 1 agg = 2; total = 4
        assert mock_call.call_count == 4

    @patch("tools.mixture_of_agents_tool._call_model", side_effect=_failing_call_model)
    def test_all_references_fail(self, mock_call):
        """Returns error when all reference models fail."""
        result = mixture_of_agents(
            prompt="test",
            reference_models=["bad-model"],
            aggregator_model="aggregator",
        )
        assert result["ok"] is False
        assert "All reference models failed" in result["error"]

    def test_handle_returns_string(self):
        """Handler returns a JSON string."""
        with patch("tools.mixture_of_agents_tool._call_model", side_effect=_fake_call_model):
            output = _handle_mixture_of_agents({"prompt": "test", "reference_models": ["m1"]})
            assert isinstance(output, str)
            data = json.loads(output)
            assert data["ok"] is True

    def test_handle_empty_prompt(self):
        """Handler returns error for empty prompt."""
        output = _handle_mixture_of_agents({"prompt": ""})
        data = json.loads(output)
        assert "error" in data

    def test_schema_structure(self):
        """Schema has required fields."""
        assert MIXTURE_OF_AGENTS_SCHEMA["name"] == "mixture_of_agents"
        assert "prompt" in MIXTURE_OF_AGENTS_SCHEMA["parameters"]["properties"]
        assert "prompt" in MIXTURE_OF_AGENTS_SCHEMA["parameters"]["required"]

    def test_registered_in_registry(self):
        """Tool is registered in the registry."""
        from tools.registry import registry
        entry = registry.get_entry("mixture_of_agents")
        assert entry is not None
        assert entry.toolset == "llm"
