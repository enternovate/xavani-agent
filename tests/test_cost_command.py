# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for per-turn token accounting and the /cost command renderer (Task 10).

Covers:
  (a) ``accumulate_session_usage`` — feeding a fake usage dict/object into the
      accounting function accumulates session totals and the per-turn meter
      correctly (streaming + tool-call turns all flow through the same path).
  (b) ``render_cost_report`` — the /cost handler's thin renderer builds the
      expected fields from plain totals + a precomputed CostResult, so the
      handler itself stays testable without a live agent.
  (c) a hermetic ``estimate_usage_cost`` check against the official-docs
      pricing snapshot (no network: deepseek-v4-pro pricing is encoded).
"""
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest

# Ensure repo root is importable (conftest also does this — belt and braces).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Stub out optional heavy dependencies not installed in the test environment
sys.modules.setdefault("fire", types.SimpleNamespace(Fire=lambda *a, **k: None))
sys.modules.setdefault("firecrawl", types.SimpleNamespace(Firecrawl=object))
sys.modules.setdefault("fal_client", types.SimpleNamespace())

from run_agent import accumulate_session_usage, render_cost_report  # noqa: E402
from agent.usage_pricing import CanonicalUsage, CostResult, estimate_usage_cost  # noqa: E402


def _make_agent():
    """A minimal fake agent carrying the session_* accounting attributes."""
    return types.SimpleNamespace(
        session_input_tokens=0,
        session_output_tokens=0,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
        session_reasoning_tokens=0,
        session_prompt_tokens=0,
        session_completion_tokens=0,
        session_total_tokens=0,
        session_api_calls=0,
        session_turn_usage=[],
    )


class TestAccounting:
    """Per-turn accumulation from fake usage dicts/objects."""

    def test_accumulates_totals_across_calls(self):
        agent = _make_agent()
        accumulate_session_usage(
            agent,
            {"input_tokens": 100, "output_tokens": 50,
             "cache_read_tokens": 20, "cache_write_tokens": 10},
        )
        accumulate_session_usage(
            agent,
            {"input_tokens": 200, "output_tokens": 25,
             "cache_read_tokens": 40, "cache_write_tokens": 5},
        )
        assert agent.session_input_tokens == 300
        assert agent.session_output_tokens == 75
        assert agent.session_cache_read_tokens == 60
        assert agent.session_cache_write_tokens == 15
        assert agent.session_api_calls == 2
        # prompt = input + cache_read + cache_write; total = prompt + output
        assert agent.session_prompt_tokens == 375
        assert agent.session_completion_tokens == 75
        assert agent.session_total_tokens == 450

    def test_accepts_canonical_usage_object(self):
        agent = _make_agent()
        usage = CanonicalUsage(
            input_tokens=10, output_tokens=5,
            cache_read_tokens=3, cache_write_tokens=2,
        )
        entry = accumulate_session_usage(agent, usage)
        assert entry == {
            "input": 10, "output": 5, "cache_read": 3,
            "cache_write": 2, "reasoning": 0, "total": 20,
        }
        assert agent.session_input_tokens == 10
        assert agent.session_total_tokens == 20

    def test_per_turn_meter_records_each_call(self):
        agent = _make_agent()
        accumulate_session_usage(agent, {"input_tokens": 100, "output_tokens": 10})
        accumulate_session_usage(agent, {"input_tokens": 50, "output_tokens": 20})
        assert [t["input"] for t in agent.session_turn_usage] == [100, 50]
        assert agent.session_turn_usage[1]["total"] == 70

    def test_creates_missing_attributes(self):
        agent = types.SimpleNamespace()
        accumulate_session_usage(agent, {"input_tokens": 5, "output_tokens": 2})
        assert agent.session_input_tokens == 5
        assert agent.session_output_tokens == 2
        assert agent.session_api_calls == 1
        assert agent.session_turn_usage[0]["input"] == 5

    def test_tool_call_turn_is_just_another_response(self):
        # Tool-call turns flow through the same accumulation path — nothing
        # special-cases them, so totals and the meter stay consistent.
        agent = _make_agent()
        accumulate_session_usage(agent, {"input_tokens": 900, "output_tokens": 60})
        accumulate_session_usage(agent, {"input_tokens": 950, "output_tokens": 12})
        accumulate_session_usage(agent, {"input_tokens": 980, "output_tokens": 400})
        assert len(agent.session_turn_usage) == 3
        assert agent.session_api_calls == 3
        assert agent.session_input_tokens == 900 + 950 + 980


class TestCostReport:
    """/cost renderer output — built from plain totals + CostResult."""

    def test_renders_expected_fields(self):
        totals = {
            "input_tokens": 1_000,
            "output_tokens": 500,
            "cache_read_tokens": 200,
            "cache_write_tokens": 100,
            "reasoning_tokens": 50,
            "total_tokens": 1_800,
            "api_calls": 3,
        }
        cost = CostResult(
            amount_usd=Decimal("0.0123"),
            status="estimated",
            source="official_docs_snapshot",
            label="~$0.01",
        )
        lines = render_cost_report(
            model="deepseek-v4-pro",
            totals=totals,
            per_turn=[
                {"input": 400, "output": 200, "cache_read": 100,
                 "cache_write": 50, "reasoning": 0, "total": 750},
                {"input": 600, "output": 300, "cache_read": 100,
                 "cache_write": 50, "reasoning": 50, "total": 1050},
            ],
            cost_result=cost,
        )
        text = "\n".join(lines)
        assert "Session Cost" in text
        assert "deepseek-v4-pro" in text
        assert "Input tokens:" in text and "1,000" in text
        assert "Output tokens:" in text and "500" in text
        assert "Cache read tokens:" in text and "200" in text
        assert "Cache write tokens:" in text and "100" in text
        assert "Total tokens:" in text and "1,800" in text
        assert "Total cost:" in text and "0.0123" in text
        assert "official_docs_snapshot" in text
        assert "Per-turn tokens" in text
        assert "#1" in text and "#2" in text

    def test_unknown_cost_renders_n_a(self):
        lines = render_cost_report(
            model="mystery-model",
            totals={"input_tokens": 10},
            cost_result=CostResult(amount_usd=None, status="unknown",
                                   source="none", label="n/a"),
        )
        assert "Total cost:" in "\n".join(lines)

    def test_included_cost(self):
        lines = render_cost_report(
            model="gpt-codex",
            totals={"input_tokens": 10},
            cost_result=CostResult(amount_usd=Decimal("0"), status="included",
                                   source="none", label="included"),
        )
        assert "included" in "\n".join(lines)

    def test_no_turns_yet(self):
        lines = render_cost_report(model="m", totals={"input_tokens": 0}, per_turn=[])
        assert "no turns recorded" in "\n".join(lines)


class TestCostEstimation:
    """Hermetic cost estimation against the official-docs snapshot."""

    def test_estimate_usage_cost_deepseek_snapshot(self):
        usage = CanonicalUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        result = estimate_usage_cost("deepseek-v4-pro", usage, provider="deepseek")
        assert result.amount_usd == Decimal("5.22")
        assert result.status == "estimated"
        assert result.source == "official_docs_snapshot"
