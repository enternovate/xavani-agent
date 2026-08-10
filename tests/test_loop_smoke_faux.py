# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Smoke tests driving the REAL AIAgent loop with a scripted faux provider.

No API keys, no network. ``run_agent.OpenAI`` is patched with the harness
client factory, so every client the loop constructs (primary + per-request)
resolves to a shared :class:`~tests.harness.faux_provider.FauxProvider` that
replays a scripted sequence of assistant responses.  The loop's real
transport seam (``_interruptible_api_call`` → ``chat.completions.create``),
real tool dispatch (``skills_list``), and the error-retry path are all
exercised.
"""

import json
from unittest.mock import patch

import pytest

from run_agent import AIAgent
from tests.harness.faux_provider import ScriptedSession


class _RateLimitError(Exception):
    """Minimal OpenAI-shaped 429 error.  The loop's error classifier reads
    the ``status_code`` attribute (same shape as the SDK's
    ``openai.RateLimitError``)."""

    status_code = 429

    def __str__(self):
        return "Error code: 429 - Rate limit exceeded."


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


@pytest.fixture()
def make_agent():
    """Build an AIAgent whose provider is a fresh ScriptedSession.

    The ``run_agent.OpenAI`` patch must stay active BEYOND agent
    construction: clients are created lazily on the first
    ``chat.completions.create`` call during ``run_conversation``, not at
    ``AIAgent()`` time.  The fixture therefore starts the patches for the
    whole test and stops them at teardown.
    """

    def _make(session: ScriptedSession, tools=("skills_list",)):
        with (
            patch(
                "run_agent.get_tool_definitions",
                return_value=_make_tool_defs(*tools),
            ),
            patch("run_agent.check_toolset_requirements", return_value={}),
        ):
            agent = AIAgent(
                api_key="test-key-1234567890",
                base_url="https://openrouter.ai/api/v1",
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
            )
        # Keep the loop away from real session/trajectory persistence.
        agent._persist_session = lambda *a, **k: None
        agent._save_trajectory = lambda *a, **k: None
        agent._save_session_log = lambda *a, **k: None
        agent.suppress_status_output = True
        return agent

    _openai_patch = patch("run_agent.OpenAI", new=object())  # placeholder
    _openai_patch.start()

    def _with_provider(session: ScriptedSession, tools=("skills_list",)):
        nonlocal _openai_patch
        factory = session.client_factory()
        _openai_patch.stop()
        _openai_patch = patch("run_agent.OpenAI", factory)
        _openai_patch.start()
        return _make(session, tools=tools)

    yield _with_provider
    try:
        _openai_patch.stop()
    except Exception:
        pass


def test_loop_executes_scripted_tool_call_and_returns_final_text(make_agent):
    """The loop should run a scripted tool call through the REAL dispatcher
    (skills_list — read-only), feed the result back to the provider, then
    return the scripted final text."""
    session = ScriptedSession()
    session.tool_call("skills_list", {})
    session.text("all done, boss")

    agent = make_agent(session)
    result = agent.run_conversation("list your skills")

    assert result["completed"] is True
    assert result["final_response"] == "all done, boss"

    provider = session.provider
    # Turn 1: tool-call response.  Turn 2: final text.  No more calls.
    assert len(provider.calls) == 2

    # The second request must carry the tool result back to the provider.
    second_call_messages = provider.calls[1]["messages"]
    tool_results = [m for m in second_call_messages if m.get("role") == "tool"]
    assert tool_results, "tool result was not fed back to the provider"
    assert tool_results[0].get("tool_call_id")
    content = tool_results[0]["content"]
    parsed = json.loads(content) if isinstance(content, str) else content
    assert parsed.get("success") is True

    # The user's message reached the provider on the first call.
    first_call_messages = provider.calls[0]["messages"]
    assert any(
        m.get("role") == "user" and "list your skills" in str(m.get("content"))
        for m in first_call_messages
    )


def test_loop_survives_provider_exception_then_succeeds(make_agent):
    """A transient provider error (429) should be retried; the next scripted
    response becomes the final answer."""
    session = ScriptedSession()
    session.raise_(_RateLimitError("rate limited"))
    session.text("recovered")

    agent = make_agent(session)
    with patch("run_agent.time.sleep", return_value=None):
        result = agent.run_conversation("hello")

    assert result["completed"] is True
    assert result["final_response"] == "recovered"
    assert len(session.provider.calls) == 2
