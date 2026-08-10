# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Length-stop guard: tool calls from a truncated assistant message must be
failed with an error result, never executed (pi failToolCallsFromTruncatedMessage).

The loop's streaming path accumulates ``finish_reason`` from the final chunk
(``choices[0].finish_reason``); a stream ending with ``finish_reason='length'``
is the token-limit truncation signal.  Every tool call in such a message is
fed back to the provider as a failed result so the model can re-issue with
complete arguments — the tool handler must never run.
"""

from unittest.mock import patch

import pytest

from run_agent import AIAgent
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


@pytest.fixture()
def make_agent():
    """Build an AIAgent whose provider is a fresh ScriptedSession.

    Mirrors tests/test_loop_smoke_faux.py: the run_agent.OpenAI patch must
    stay active BEYOND agent construction (clients are built lazily on the
    first chat.completions.create call inside run_conversation).
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


def test_length_stop_fails_tool_calls_without_executing_them(make_agent):
    """A streamed response ending with finish_reason 'length' plus a tool call
    must feed back a failed ('truncated') tool result and continue the loop —
    the skills_list handler must never run."""
    session = ScriptedSession()
    session.stream_tool_call_truncated("skills_list", {})
    session.text("recovered after truncation")

    agent = make_agent(session)
    result = agent.run_conversation("list your skills")

    assert result["completed"] is True
    assert result["final_response"] == "recovered after truncation"

    provider = session.provider
    assert len(provider.calls) == 2

    # The tool result fed back on the second request must be the truncation
    # error marker — the real skills_list handler never ran.
    second_call_messages = provider.calls[1]["messages"]
    tool_results = [m for m in second_call_messages if m.get("role") == "tool"]
    assert tool_results, "truncated tool call was not fed back as a failed result"
    assert "truncated" in tool_results[0]["content"]
