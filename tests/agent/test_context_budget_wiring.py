# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Wiring tests for the context-budget governor UI (harness item 4)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace


def _make_cli_with_compressor(used_tokens: int, limit_tokens: int):
    """Build a bare CLI instance with a stubbed agent and compressor."""
    import cli as cli_mod

    inst = cli_mod.XavaniCLI.__new__(cli_mod.XavaniCLI)
    inst.model = "test-model"
    inst.session_start = datetime.now()
    inst._prompt_start_time = None
    inst._prompt_duration = 0.0
    inst._background_tasks = {}
    inst.conversation_history = []
    inst.verbose = False
    inst.agent = SimpleNamespace(
        model="test-model",
        provider=None,
        base_url=None,
        api_key=None,
        session_api_calls=1,
        get_rate_limit_state=lambda: None,
        system_prompt="",
        session_prompt_tokens=0,
        session_completion_tokens=0,
        session_total_tokens=0,
        context_compressor=SimpleNamespace(
            last_prompt_tokens=used_tokens,
            context_length=limit_tokens,
            compression_count=0,
        ),
    )
    return inst


class _CostResult:
    """Minimal pricing result for the usage display."""

    status = "unknown"
    source = "unknown"
    amount_usd = None


def test_status_bar_snapshot_reports_warn_level() -> None:
    """90% of the budget classifies as warn in the status bar snapshot."""
    inst = _make_cli_with_compressor(90000, 100000)
    snapshot = inst._get_status_bar_snapshot()
    assert snapshot["context_budget_level"] == "warn"


def test_status_bar_snapshot_reports_block_level() -> None:
    """96% of the budget classifies as block in the status bar snapshot."""
    inst = _make_cli_with_compressor(96000, 100000)
    snapshot = inst._get_status_bar_snapshot()
    assert snapshot["context_budget_level"] == "block"


def test_status_bar_snapshot_defaults_ok_without_agent() -> None:
    """No agent means no budget pressure — level stays ok."""
    import cli as cli_mod

    inst = cli_mod.XavaniCLI.__new__(cli_mod.XavaniCLI)
    inst.model = "test-model"
    inst.session_start = datetime.now()
    inst._prompt_start_time = None
    inst._prompt_duration = 0.0
    inst._background_tasks = {}
    inst.agent = None
    snapshot = inst._get_status_bar_snapshot()
    assert snapshot["context_budget_level"] == "ok"


def test_show_usage_prints_budget_warning_line(monkeypatch, capsys) -> None:
    """/usage shows the budget warning when the context is at 90%."""
    inst = _make_cli_with_compressor(90000, 100000)
    monkeypatch.setattr(
        "agent.usage_pricing.estimate_usage_cost",
        lambda *args, **kwargs: _CostResult(),
    )
    inst._show_usage()
    out = capsys.readouterr().out
    assert "Context budget:" in out
    assert "WARN" in out


def test_show_usage_omits_budget_line_when_ok(monkeypatch, capsys) -> None:
    """/usage stays quiet about the budget when the context is healthy."""
    inst = _make_cli_with_compressor(10000, 100000)
    monkeypatch.setattr(
        "agent.usage_pricing.estimate_usage_cost",
        lambda *args, **kwargs: _CostResult(),
    )
    inst._show_usage()
    out = capsys.readouterr().out
    assert "Context budget:" not in out
