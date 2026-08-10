# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for surfacing provider cache hits in /status."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import cli as cli_module
from cli import XavaniCLI


def _make_cli():
    cli_obj = XavaniCLI.__new__(XavaniCLI)
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj.agent = None
    cli_obj.conversation_history = []
    cli_obj.session_id = "session-123"
    cli_obj._pending_input = MagicMock()
    cli_obj._status_bar_visible = True
    cli_obj.model = "openai/gpt-5.4"
    cli_obj.provider = "openai"
    cli_obj.session_start = datetime(2026, 4, 9, 19, 24)
    cli_obj._agent_running = False
    cli_obj._session_db = MagicMock()
    cli_obj._session_db.get_session.return_value = None
    return cli_obj


def _printed(cli_obj):
    return "\n".join(str(call.args[0]) for call in cli_obj.console.print.call_args_list)


def test_show_session_status_renders_provider_cache_hits_line():
    cli_obj = _make_cli()
    cli_obj.agent = SimpleNamespace(
        session_total_tokens=321,
        session_api_calls=4,
        _or_cache_hits=3,
        session_cache_read_tokens=12_500,
        session_cache_write_tokens=2_000,
    )

    with patch.object(cli_module, "display_xavani_home", return_value="~/.xavani"):
        cli_obj._show_session_status()

    printed = _printed(cli_obj)
    assert "Provider cache hits: 3" in printed
    assert "cache read ~12,500 tokens" in printed


def test_show_session_status_omits_cache_line_when_agent_has_no_hits():
    cli_obj = _make_cli()
    cli_obj.agent = SimpleNamespace(
        session_total_tokens=321,
        session_api_calls=4,
        _or_cache_hits=0,
        session_cache_read_tokens=0,
        session_cache_write_tokens=0,
    )

    with patch.object(cli_module, "display_xavani_home", return_value="~/.xavani"):
        cli_obj._show_session_status()

    assert "Provider cache hits" not in _printed(cli_obj)


def test_show_session_status_omits_cache_line_when_no_agent():
    cli_obj = _make_cli()

    with patch.object(cli_module, "display_xavani_home", return_value="~/.xavani"):
        cli_obj._show_session_status()

    assert "Provider cache hits" not in _printed(cli_obj)
