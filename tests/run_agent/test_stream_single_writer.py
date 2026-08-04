# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A02: stream single-writer fence.

A stream attempt claims the delta sink; a newer attempt supersedes it.
The stale writer's chunks are dropped at the emit chokepoint so
superseded streams cannot emit interleaved ghost text after an interrupt
or retry. Best-effort helpers guarantee a guard-less agent is never
fenced (and never crashes).
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from agent.stream_single_writer import (
    claim_stream_writer,
    stream_writer_is_current,
    stream_writer_superseded,
)
from run_agent import AIAgent


@pytest.fixture()
def agent():
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        a = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        a.client = MagicMock()
        return a


def test_claim_is_monotonic_and_thread_local(agent):
    token_a = agent._claim_stream_writer()
    token_b = agent._claim_stream_writer()
    assert token_b > token_a
    # The second claim happened on the same thread: this thread is current.
    assert agent._stream_writer_is_current(token_b)
    assert not agent._stream_writer_superseded()


def test_new_claim_supersedes_previous_writer(agent):
    agent._claim_stream_writer()  # writer A (current thread)
    agent._stream_writer_tls.token = None  # simulate a different stream thread
    writer_b = agent._claim_stream_writer()  # writer B
    # A's token is stale now.
    assert not agent._stream_writer_is_current(1)
    assert agent._stream_writer_is_current(writer_b)


def test_superseded_thread_drops_deltas(agent):
    received = []

    def _cb(text):
        received.append(text)

    agent.stream_delta_callback = _cb

    # Writer A claims and streams from its own thread.
    start = threading.Event()
    phase1 = threading.Event()
    emit_again = threading.Event()
    done = threading.Event()
    token_a = {}

    def _writer_a():
        start.wait()
        token_a["value"] = agent._claim_stream_writer()
        agent._fire_stream_delta("hello")
        phase1.set()
        emit_again.wait()
        agent._fire_stream_delta("ghost")
        done.set()

    t = threading.Thread(target=_writer_a)
    t.start()
    start.set()
    assert phase1.wait(timeout=10)
    t.join(timeout=1)
    assert received == ["hello"]
    assert token_a["value"] > 0

    # A newer stream attempt claims on the main thread.
    token_b = agent._claim_stream_writer()
    assert token_b > token_a["value"]

    # Writer A's thread emits again — its stale token fences the delta out.
    emit_again.set()
    assert done.wait(timeout=10)
    assert received == ["hello"], "stale writer's delta must be dropped"


def test_dropped_delta_is_counted(agent):
    agent._claim_stream_writer()  # token 1 on this thread
    agent._claim_stream_writer()  # token 2 — this thread is the current writer
    agent._stream_writer_tls.token = 1  # pretend this thread holds the old token
    agent._fire_stream_delta("dropped")
    assert agent._stream_writer_dropped == 1


def test_best_effort_claim_without_fence():
    stub = object()
    assert claim_stream_writer(stub) == 0
    assert stream_writer_is_current(stub, 0) is True
    assert stream_writer_superseded(stub) is False


def test_best_effort_claim_with_fence_agent(agent):
    token = claim_stream_writer(agent)
    assert token > 0
    assert stream_writer_is_current(agent, token) is True
    assert stream_writer_superseded(agent) is False


def test_fence_does_not_break_plain_delta_flow(agent):
    received = []

    def _cb(text):
        received.append(text)

    agent.stream_delta_callback = _cb
    agent._fire_stream_delta("one")
    agent._fire_stream_delta("two")
    assert received == ["one", "two"]
