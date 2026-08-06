# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Wiring tests for the config-gated self-critique pass (harness item 3)."""

from __future__ import annotations

from agent.conversation_loop import _maybe_self_critique


class _FakeAgent:
    """Minimal agent stub with the attributes the reviewer reads."""

    model = "test-model"
    provider = "test-provider"
    base_url = None


def _set_harness_enabled(monkeypatch, enabled: bool = True) -> None:
    import xavani_cli.config as config_mod

    monkeypatch.setattr(
        config_mod,
        "load_config",
        lambda: {"harness": {"self_critique": enabled}},
    )


def test_disabled_returns_answer_unchanged(monkeypatch) -> None:
    """The pass is off by default — the answer passes through untouched."""
    import xavani_cli.config as config_mod

    monkeypatch.setattr(config_mod, "load_config", lambda: {})
    assert _maybe_self_critique(_FakeAgent(), "original answer") == "original answer"


def test_enabled_ok_review_keeps_answer(monkeypatch) -> None:
    """An OK review keeps the answer and still exercises the reviewer."""
    _set_harness_enabled(monkeypatch)
    seen = {}

    def _fake_run(answer, reviewer, rubric=None, enabled=True, max_iterations=1):
        seen["reviewer_called"] = reviewer("probe")
        return {"answer": answer, "fixed": False, "iterations": 0}

    monkeypatch.setattr("agent.self_critique.run_self_critique", _fake_run)
    monkeypatch.setattr(
        "tools.mixture_of_agents_tool._call_model",
        lambda model, prompt, system="", provider=None, base_url=None, api_key=None, timeout=60: {
            "response": "OK",
            "ok": True,
        },
    )
    result = _maybe_self_critique(_FakeAgent(), "original answer")
    assert result == "original answer"
    assert seen["reviewer_called"] == "OK"


def test_enabled_fix_replaces_answer(monkeypatch) -> None:
    """A FIX review replaces the final answer once (bounded loop)."""
    _set_harness_enabled(monkeypatch)

    def _fake_run(answer, reviewer, rubric=None, enabled=True, max_iterations=1):
        return {"answer": "fixed answer", "fixed": True, "iterations": 1}

    monkeypatch.setattr("agent.self_critique.run_self_critique", _fake_run)
    assert _maybe_self_critique(_FakeAgent(), "original answer") == "fixed answer"


def test_reviewer_passes_agent_model_and_provider(monkeypatch) -> None:
    """The reviewer routes through the agent's active model configuration."""
    _set_harness_enabled(monkeypatch)
    seen = {}

    def _fake_run(answer, reviewer, rubric=None, enabled=True, max_iterations=1):
        seen["review_result"] = reviewer("prompt")
        return {"answer": answer, "fixed": False, "iterations": 0}

    def _fake_call_model(model, prompt, system="", provider=None, base_url=None, api_key=None, timeout=60):
        seen["model"] = model
        seen["provider"] = provider
        return {"response": "review text", "ok": True}

    monkeypatch.setattr("agent.self_critique.run_self_critique", _fake_run)
    monkeypatch.setattr("tools.mixture_of_agents_tool._call_model", _fake_call_model)
    _maybe_self_critique(_FakeAgent(), "original answer")
    assert seen["review_result"] == "review text"
    assert seen["model"] == "test-model"
    assert seen["provider"] == "test-provider"


def test_critique_failure_keeps_answer(monkeypatch) -> None:
    """A model failure inside the pass must never break the conversation."""
    _set_harness_enabled(monkeypatch)

    def _fake_run(answer, reviewer, rubric=None, enabled=True, max_iterations=1):
        reviewer("prompt")
        return {"answer": "never", "fixed": False, "iterations": 0}

    def _boom(model, prompt, system="", provider=None, base_url=None, api_key=None, timeout=60):
        raise RuntimeError("model down")

    monkeypatch.setattr("agent.self_critique.run_self_critique", _fake_run)
    monkeypatch.setattr("tools.mixture_of_agents_tool._call_model", _boom)
    assert _maybe_self_critique(_FakeAgent(), "original answer") == "original answer"


def test_empty_answer_skips_pass(monkeypatch) -> None:
    """An empty answer returns immediately without touching config."""
    import xavani_cli.config as config_mod

    def _unexpected():
        raise AssertionError("config must not load for an empty answer")

    monkeypatch.setattr(config_mod, "load_config", _unexpected)
    assert _maybe_self_critique(_FakeAgent(), "") == ""
