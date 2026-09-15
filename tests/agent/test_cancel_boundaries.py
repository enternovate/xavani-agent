# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Cancellation and recovery boundaries in the real agent loop (R1 Task 08).

Pins what a cancelled turn is allowed to do.  Every test drives the REAL
``run_conversation`` loop through the faux-provider harness
(``tests/harness/faux_provider.py``): real transport seam, real tool
dispatch, real interrupt bookkeeping.  No sleeps — interrupts land from
callbacks or before the loop starts, so the ordering is deterministic.

Covered boundaries:

1. Interrupt requested BEFORE the turn starts → no provider call at all.
2. Interrupt landing on ``tool.completed`` of a sequential batch → the
   remaining calls in that batch are skipped, no further provider call.
3. A tool that finishes exactly as the stop lands still records its real
   result — once, and never a synthetic re-run.
4. A queued /steer is NOT consumed by the cancelled turn: it is handed
   back on the result so the next turn can deliver it.
5. A provider failure mid-turn keeps the transcript and the session
   identity, and retries the REQUEST without re-executing tools.

Already covered elsewhere (not duplicated here):

* ``tests/run_agent/test_concurrent_interrupt.py::test_concurrent_preflight_interrupt_skips_all``
  — concurrent pre-flight skip message shape.
* ``tests/run_agent/test_steer.py::TestSteerClearedOnInterrupt::test_clear_interrupt_drops_pending_steer``
  — ``clear_interrupt()`` itself drops a pending steer.
* ``tests/gateway/test_sse_agent_cancel.py`` — SSE disconnect cancels the
  agent task and calls ``agent.interrupt()``.
"""

import json
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

    Mirrors ``tests/test_loop_smoke_faux.py``: the ``run_agent.OpenAI``
    patch must stay active BEYOND agent construction, because clients are
    created lazily on the first ``chat.completions.create`` inside
    ``run_conversation``.
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


class _ProgressRecorder:
    """Records tool progress events and can interrupt on a chosen one."""

    def __init__(self, interrupt_on=None, agent=None):
        self.events = []
        self._interrupt_on = interrupt_on
        self._agent = agent

    def __call__(self, event, name, preview=None, args=None, **kwargs):
        self.events.append((event, name, kwargs.get("tool_call_id")))
        if self._interrupt_on == (event, name):
            self._agent.interrupt("stop")

    def names(self, event):
        return [n for e, n, _ in self.events if e == event]

    def call_ids(self, event):
        return [cid for e, _, cid in self.events if e == event]


def _tool_messages(messages, name=None):
    return [
        m for m in messages
        if m.get("role") == "tool" and (name is None or m.get("name") == name)
    ]


# ---------------------------------------------------------------------------
# 1. Interrupt requested before the turn starts
# ---------------------------------------------------------------------------


def test_interrupt_before_turn_never_calls_provider(make_agent):
    """A stop that lands before run_conversation() must prevent the first
    provider call entirely — the loop checks _interrupt_requested before it
    builds api_messages or touches the network."""
    session = ScriptedSession()
    session.text("this response must never be requested")

    agent = make_agent(session)
    agent.interrupt("stop before start")

    result = agent.run_conversation("do work")

    assert session.provider.calls == [], "provider was called after a pre-turn stop"
    assert result["interrupted"] is True
    assert result["turn_exit_reason"] == "interrupted_by_user"
    assert result["api_calls"] == 0
    assert result["completed"] is False
    # The stop is consumed by the turn it cancelled — the next turn starts clean.
    assert agent._interrupt_requested is False
    assert agent._pending_steer is None


# ---------------------------------------------------------------------------
# 2. Interrupt landing on tool.completed of a sequential batch
# ---------------------------------------------------------------------------


def test_stop_after_first_tool_skips_rest_of_batch(make_agent, tmp_path):
    """Two sequential read_file calls on the SAME path — overlapping paths are
    never parallelised, and the differing pagination keeps them from being
    deduplicated.  A stop raised from the first ``tool.completed`` callback
    must skip the second call — marked with the 'Tool execution skipped'
    message — and end the turn without another provider call."""
    target = tmp_path / "cancel_probe.txt"
    target.write_text("first line\nsecond line\n", encoding="utf-8")

    session = ScriptedSession()
    session.tool_calls(
        ("read_file", {"path": str(target)}),
        ("read_file", {"path": str(target), "offset": 2}),
    )
    session.text("unreachable follow-up")

    agent = make_agent(session, tools=("read_file",))
    recorder = _ProgressRecorder(interrupt_on=("tool.completed", "read_file"), agent=agent)
    agent.tool_progress_callback = recorder

    result = agent.run_conversation("read that file twice")

    assert len(session.provider.calls) == 1, "loop kept calling the provider after the stop"
    assert result["interrupted"] is True
    assert result["turn_exit_reason"] == "interrupted_by_user"

    # Exactly one dispatch: the second call was never started.
    assert recorder.names("tool.started") == ["read_file"]
    assert recorder.call_ids("tool.completed") == ["call_0"]

    tool_msgs = _tool_messages(result["messages"], "read_file")
    assert len(tool_msgs) == 2, "skipped call must still be answered for protocol validity"
    assert "first line" in tool_msgs[0]["content"]
    assert "Tool execution skipped" in tool_msgs[1]["content"]
    assert tool_msgs[1]["tool_call_id"] == "call_1"


# ---------------------------------------------------------------------------
# 3. Late result: the tool that finished keeps its real result
# ---------------------------------------------------------------------------


def test_late_tool_result_recorded_once_without_rerun(make_agent):
    """The stop lands while the only tool of the batch is completing.  Its
    real result must be recorded exactly once, with no second dispatch and
    no synthetic replacement of the result."""
    session = ScriptedSession()
    session.tool_call("skills_list", {})
    session.text("unreachable follow-up")

    agent = make_agent(session, tools=("skills_list",))
    recorder = _ProgressRecorder(interrupt_on=("tool.completed", "skills_list"), agent=agent)
    agent.tool_progress_callback = recorder

    result = agent.run_conversation("list your skills")

    assert result["interrupted"] is True
    assert len(session.provider.calls) == 1

    assert recorder.names("tool.started") == ["skills_list"]
    assert recorder.names("tool.completed") == ["skills_list"]

    tool_msgs = _tool_messages(result["messages"], "skills_list")
    assert len(tool_msgs) == 1, "the completed call must be answered exactly once"
    payload = tool_msgs[0]["content"]
    parsed = json.loads(payload) if isinstance(payload, str) else payload
    assert parsed.get("success") is True, f"real tool result was replaced: {payload!r}"
    assert "skipped" not in str(payload)


# ---------------------------------------------------------------------------
# 4. Steering survives a cancelled turn
# ---------------------------------------------------------------------------


def test_steer_is_handed_back_when_turn_is_cancelled(make_agent):
    """A /steer queued for the next tool batch has no batch left to land in
    once the turn is stopped.  It must come back on the result (deliverable
    to the following turn) instead of being consumed — or dropped — by the
    cancelled turn."""
    session = ScriptedSession()
    session.text("this response must never be requested")

    agent = make_agent(session)
    assert agent.steer("check the logs before retrying") is True
    agent.interrupt("stop")

    result = agent.run_conversation("do work")

    assert session.provider.calls == []
    assert result["interrupted"] is True
    assert result["pending_steer"] == "check the logs before retrying"
    # The slot is cleared as part of the hand-off, so the same steer cannot
    # be delivered twice.
    assert agent._pending_steer is None


# ---------------------------------------------------------------------------
# 5. Provider failure mid-turn preserves transcript and session identity
# ---------------------------------------------------------------------------


def test_provider_failure_mid_turn_keeps_transcript_without_rerunning_tools(make_agent):
    """The provider dies after a tool round.  The turn fails, but the
    transcript up to the failure survives in the result, the session
    identity is unchanged, and the retry re-sends the REQUEST — it does not
    execute the tool again."""
    session = ScriptedSession()
    session.tool_call("skills_list", {})
    for _ in range(2):
        session.raise_(TimeoutError("provider stalled"))

    agent = make_agent(session, tools=("skills_list",))
    # Pin the retry budget to one failed attempt so the test needs no
    # backoff patching: attempt 1 fails → retry_count(1) >= max_retries(1).
    agent._api_max_retries = 1
    recorder = _ProgressRecorder(agent=agent)
    agent.tool_progress_callback = recorder

    session_id_before = agent.session_id
    result = agent.run_conversation(
        "list your skills then fail",
        conversation_history=[{"role": "user", "content": "earlier turn"}],
    )

    assert result["failed"] is True
    assert result.get("error")
    assert "API call failed" in (result["final_response"] or "")

    # Identity: same session, and the transcript handed back still carries
    # both the prior history and this turn's tool work.
    assert agent.session_id == session_id_before
    transcript = json.dumps(result["messages"], default=str)
    assert "earlier turn" in transcript, "prior history was dropped on failure"
    assert "list your skills then fail" in transcript
    assert any(m.get("role") == "assistant" and m.get("tool_calls") for m in result["messages"])
    tool_msgs = _tool_messages(result["messages"], "skills_list")
    assert len(tool_msgs) == 1
    parsed = json.loads(tool_msgs[0]["content"])
    assert parsed.get("success") is True

    # The retry re-sent the request; it did not re-execute the tool.
    assert len(session.provider.calls) == 2
    assert recorder.names("tool.started") == ["skills_list"]
    retried_messages = session.provider.calls[1]["messages"]
    assert _tool_messages(retried_messages, "skills_list"), (
        "the retry dropped the tool result instead of replaying the transcript"
    )
