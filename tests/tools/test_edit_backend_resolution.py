#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Backend-identity resolution for the ``edit`` tool (R1 Task 06).

``hashline`` and ``replace`` write with plain ``open()`` on this process's
filesystem, so an unknown/unreadable terminal backend must fail closed.
"""

import pytest

from tools import terminal_tool
from tools.edit_tool import _backend_is_local


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"env_type": "local"}, True),
        ({"env_type": "docker"}, False),
        ({"env_type": "ssh"}, False),
        ({}, False),
        ({"env_type": None}, False),
    ],
)
def test_backend_resolution_by_env_type(monkeypatch, config, expected):
    monkeypatch.setattr(terminal_tool, "_get_env_config", lambda: config)

    assert _backend_is_local() is expected


def test_backend_resolution_fails_closed_when_config_unreadable(monkeypatch):
    def boom():
        raise RuntimeError("config unavailable")

    monkeypatch.setattr(terminal_tool, "_get_env_config", boom)

    assert _backend_is_local("task-1") is False
