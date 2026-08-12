# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

import queue
import threading
from unittest.mock import patch

import cli as cli_mod
from cli import XavaniCLI


def _make_cli_stub():
    cli = XavaniCLI.__new__(XavaniCLI)
    cli._agent_running = False
    cli._approval_state = None
    cli._background_tasks = {}
    return cli


class _FakeConsole:
    def __init__(self, lines):
        self._lines = lines

    def print(self, *args, **kwargs):
        self._lines.append(" ".join(str(a) for a in args))


def _capture_help(cli, plan_mode=False):
    lines = []

    with (
        patch.object(cli_mod, "_cprint", side_effect=lambda text: lines.append(str(text))),
        patch.object(cli_mod, "ChatConsole", lambda: _FakeConsole(lines)),
        patch.object(cli_mod, "get_skill_bundles", return_value=[]),
        patch.object(cli_mod, "_skill_commands", {}),
        patch.object(cli_mod, "_is_termux_environment", return_value=False),
        patch("tools.registry.is_plan_mode", return_value=plan_mode),
    ):
        cli.show_help()
    return lines


def test_idle_state_shows_chat_basics_only():
    cli = _make_cli_stub()
    lines = _capture_help(cli)
    out = "\n".join(lines)

    assert "Available Commands" in out
    assert "Idle" in out
    idle_start = next(i for i, line in enumerate(lines) if "Idle" in line)
    category_start = next(
        i
        for i, line in enumerate(lines[idle_start + 1:], start=idle_start + 1)
        if "── " in line
    )
    idle_block = "\n".join(lines[idle_start:category_start])
    assert "/new" in idle_block
    assert "/model" in idle_block
    assert "/stop" not in idle_block
    assert "/steer" not in idle_block
    assert "/approve" not in idle_block
    assert "/deny" not in idle_block
    assert "/plan off" not in idle_block
    assert "/background" not in idle_block
    assert "/agents" not in idle_block


def test_agent_running_shows_stop_steer_queue():
    cli = _make_cli_stub()
    cli._agent_running = True
    out = "\n".join(_capture_help(cli))

    assert "/stop" in out
    assert "/steer" in out
    assert "/queue" in out
    assert "Agent is running" in out
    assert "Idle" not in out


def test_plan_mode_shows_read_only_note_and_plan_off():
    cli = _make_cli_stub()
    out = "\n".join(_capture_help(cli, plan_mode=True))

    assert "read-only" in out
    assert "/plan off" in out


def test_pending_approval_shows_approve_deny():
    cli = _make_cli_stub()
    cli._approval_state = {"response_queue": queue.Queue()}
    out = "\n".join(_capture_help(cli))

    assert "/approve" in out
    assert "/deny" in out


def test_background_tasks_show_agents_and_background():
    cli = _make_cli_stub()
    cli._background_tasks = {"bg1": threading.Thread(target=lambda: None)}
    out = "\n".join(_capture_help(cli))

    assert "/agents" in out
    assert "/background" in out
    assert "Background tasks" in out


def test_contextual_section_precedes_full_command_list():
    from xavani_cli.commands import COMMANDS_BY_CATEGORY

    cli = _make_cli_stub()
    lines = _capture_help(cli)

    idle_idx = next(i for i, line in enumerate(lines) if "Idle" in line)
    first_category_idx = next(
        i
        for i, line in enumerate(lines)
        if any(f"── {cat} ──" in line for cat in COMMANDS_BY_CATEGORY)
    )
    assert idle_idx < first_category_idx
