# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""S2-8: fast one-shot query path (``-q``/``--query``) regression tests.

Drives the REAL one-shot entry (``cli.main(query=..., quiet=True)``) in
process with a scripted faux provider, so the tests exercise the actual
bootstrap -> agent-init -> run_conversation -> exit chain with zero API
keys and zero network.

The one-shot path is already minimal: the welcome banner is skipped for
single-query mode (see the comment in ``cli.main`` above the non-quiet
branch), and the ``--quiet`` machine path prints only the final response.
These tests lock that behavior in: exit code 0, scripted final text on
stdout, and no interactive banner markup.
"""

from unittest.mock import patch

import pytest

from tests.harness.faux_provider import ScriptedSession


def _make_tool_defs(*names: str) -> list:
    """Minimal tool definitions accepted by AIAgent.__init__."""
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": f"{n} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for n in names
    ]


def _run_one_shot(capsys, final_text: str) -> int:
    """Run ``cli.main(query=..., quiet=True)`` in-process with a scripted
    provider and return the SystemExit code.

    The ``run_agent.OpenAI`` patch must stay active beyond agent
    construction: clients are created lazily on the first
    ``chat.completions.create`` during ``run_conversation``. The patches
    therefore wrap the whole ``main()`` call.
    """
    import cli  # lazy: cli.py reads config/creates dirs at import time

    session = ScriptedSession()
    session.text(final_text)
    factory = session.client_factory()

    def _fake_credentials(self):
        # Populate the instance attributes `_ensure_runtime_credentials`
        # normally sets so agent-init takes the direct-credentials branch
        # (explicit api_key + base_url) and never touches the provider
        # router. The OpenAI factory patch keeps it fully offline.
        self.api_key = "test-key-1234567890"
        self.base_url = "https://openrouter.ai/api/v1"
        return True

    with (
        patch("run_agent.OpenAI", factory),
        patch("run_agent.get_tool_definitions", return_value=_make_tool_defs("skills_list")),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("cli.XavaniCLI._ensure_runtime_credentials", _fake_credentials),
    ):
        with pytest.raises(SystemExit) as excinfo:
            cli.main(query="say hi", quiet=True)
    return excinfo.value.code


def test_one_shot_quiet_exits_zero(capsys):
    """The quiet one-shot path exits 0 on a successful scripted run."""
    code = _run_one_shot(capsys, "scripted final text")
    assert code == 0


def test_one_shot_output_contains_final_text(capsys):
    """stdout carries the agent's final response, nothing else required."""
    code = _run_one_shot(capsys, "all done, boss")
    assert code == 0
    captured = capsys.readouterr()
    assert "all done, boss" in captured.out


def test_one_shot_quiet_skips_welcome_banner(capsys):
    """The banner is not rendered in the quiet one-shot path."""
    code = _run_one_shot(capsys, "done")
    assert code == 0
    captured = capsys.readouterr()
    assert "XAVANI AGENT" not in captured.out
    assert "Getting Started" not in captured.out
