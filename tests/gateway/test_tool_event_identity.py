# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for run-event envelope identity (schema_version, seq, event_id).

Every event pushed onto a run's SSE queue must carry a stable identity:
``schema_version``, a per-run monotonic ``seq``, and
``event_id = f"{run_id}:{seq}"``. Tool lifecycle events additionally carry
``tool_call_id`` (and ``path`` when the loop supplies one) so a client can
pair a completion with the call it belongs to even when parallel tool calls
finish out of order.

There is no server-side dedupe: a replayed event consumes the next seq.
"""

import asyncio
import json
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import (
    APIServerAdapter,
    cors_middleware,
    security_headers_middleware,
)


def _make_adapter() -> APIServerAdapter:
    return APIServerAdapter(PlatformConfig(enabled=True, extra={}))


def _create_runs_app(adapter: APIServerAdapter) -> web.Application:
    mws = [mw for mw in (cors_middleware, security_headers_middleware) if mw is not None]
    app = web.Application(middlewares=mws)
    app["api_server_adapter"] = adapter
    app.router.add_post("/v1/runs", adapter._handle_runs)
    app.router.add_get("/v1/runs/{run_id}", adapter._handle_get_run)
    app.router.add_get("/v1/runs/{run_id}/events", adapter._handle_run_events)
    return app


def _parse_sse_events(body: str) -> list:
    events = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return events


class _RunHarness:
    """Builds a run callback plus its SSE queue without any HTTP server."""

    def __init__(self, run_id: str):
        self.adapter = _make_adapter()
        self.run_id = run_id
        self.loop = asyncio.new_event_loop()
        self.queue = asyncio.Queue()
        self.adapter._run_streams[run_id] = self.queue
        self.callback = self.adapter._make_run_event_callback(run_id, self.loop)

    def drain(self) -> list:
        # call_soon_threadsafe defers queue writes to the loop's ready queue.
        self.loop.run_until_complete(asyncio.sleep(0))
        self.loop.run_until_complete(asyncio.sleep(0))
        events = []
        while not self.queue.empty():
            events.append(self.queue.get_nowait())
        return events

    def close(self) -> None:
        self.loop.close()


@pytest.fixture
def harness_a():
    h = _RunHarness("run_a")
    yield h
    h.close()


class TestEnvelopeIdentity:
    def test_tool_events_carry_tool_call_id_seq_and_event_id(self, harness_a):
        cb = harness_a.callback
        cb("tool.started", "tool_a", "a", {}, tool_call_id="call_a")
        cb(
            "tool.completed", "tool_b", None, None,
            duration=0.5, is_error=False, tool_call_id="call_b", path="b.py",
        )

        events = harness_a.drain()
        assert [e["event"] for e in events] == ["tool.started", "tool.completed"]

        started, completed = events
        assert started["tool_call_id"] == "call_a"
        assert started["tool"] == "tool_a"
        assert completed["tool_call_id"] == "call_b"
        assert completed["tool"] == "tool_b"
        assert completed["path"] == "b.py"

        for seq, event in enumerate(events, start=1):
            assert event["schema_version"] == 1
            assert event["seq"] == seq
            assert event["event_id"] == f"{harness_a.run_id}:{seq}"
            assert event["run_id"] == harness_a.run_id

    def test_seq_increments_across_mixed_event_types_in_queue_order(self, harness_a):
        cb = harness_a.callback
        cb("tool.started", "grep", "pattern", {}, tool_call_id="call_1")
        cb("reasoning.available", None, "thinking", None)
        cb("tool.completed", "grep", None, None, duration=0.2, tool_call_id="call_1")

        events = harness_a.drain()
        assert [e["event"] for e in events] == [
            "tool.started",
            "reasoning.available",
            "tool.completed",
        ]
        assert [e["seq"] for e in events] == [1, 2, 3]
        assert [e["event_id"] for e in events] == [
            f"{harness_a.run_id}:1",
            f"{harness_a.run_id}:2",
            f"{harness_a.run_id}:3",
        ]
        assert all(e["schema_version"] == 1 for e in events)
        assert events[1]["text"] == "thinking"
        assert events[2]["tool_call_id"] == "call_1"

    def test_per_run_counters_are_independent_when_pushes_interleave(self):
        run_a = _RunHarness("run_a")
        run_b = _RunHarness("run_b")
        try:
            run_a.callback("tool.started", "a1", None, {}, tool_call_id="call_a1")
            run_b.callback("tool.started", "b1", None, {}, tool_call_id="call_b1")
            run_a.callback("tool.started", "a2", None, {}, tool_call_id="call_a2")

            events_a = run_a.drain()
            events_b = run_b.drain()
        finally:
            run_a.close()
            run_b.close()

        assert [(e["event"], e["seq"]) for e in events_a] == [
            ("tool.started", 1),
            ("tool.started", 2),
        ]
        assert [e["event_id"] for e in events_a] == ["run_a:1", "run_a:2"]
        assert [(e["event"], e["seq"]) for e in events_b] == [("tool.started", 1)]
        assert [e["event_id"] for e in events_b] == ["run_b:1"]
        assert [e["tool_call_id"] for e in events_a] == ["call_a1", "call_a2"]

    def test_replayed_tool_completed_consumes_the_next_seq(self, harness_a):
        cb = harness_a.callback
        payload = {
            "tool": "write_file",
            "duration": 0.3,
            "is_error": False,
            "tool_call_id": "call_x",
            "path": "x.py",
        }
        cb("tool.completed", None, None, None, **payload)
        cb("tool.completed", None, None, None, **payload)

        events = harness_a.drain()
        # No dedupe server-side: a replay is a new event with a new identity.
        assert [e["seq"] for e in events] == [1, 2]
        assert [e["event_id"] for e in events] == [
            f"{harness_a.run_id}:1",
            f"{harness_a.run_id}:2",
        ]
        first, second = events
        identity = {"seq", "event_id", "timestamp"}
        assert {k: v for k, v in first.items() if k not in identity} == {
            k: v for k, v in second.items() if k not in identity
        }
        assert second["seq"] == first["seq"] + 1


class _ScriptedAgent:
    """Emits tool + text-delta events through the callbacks the gateway wires."""

    def __init__(self, **kwargs):
        self.tool_progress_callback = kwargs.get("tool_progress_callback")
        self.stream_delta_callback = kwargs.get("stream_delta_callback")
        self.session_prompt_tokens = 0
        self.session_completion_tokens = 0
        self.session_total_tokens = 0

    def run_conversation(self, user_message=None, conversation_history=None, task_id=None):
        self.tool_progress_callback(
            "tool.started", "read_file", "a.py", {"path": "a.py"}, tool_call_id="call_a",
        )
        self.stream_delta_callback("Hel")
        self.stream_delta_callback("lo")
        self.tool_progress_callback(
            "tool.completed", "read_file", None, None,
            duration=0.1, is_error=False, tool_call_id="call_a", path="a.py",
        )
        return {
            "final_response": "Hello",
            "verification_state": "passed",
            "missing_checks": [],
            "failed_checks": [],
        }


class TestEnvelopeOnLiveRunStream:
    @pytest.mark.asyncio
    async def test_every_streamed_event_carries_the_run_envelope(self):
        adapter = _make_adapter()
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(
                adapter, "_create_agent", side_effect=lambda **kw: _ScriptedAgent(**kw)
            ):
                resp = await cli.post("/v1/runs", json={"input": "hello"})
                assert resp.status == 202
                run_id = (await resp.json())["run_id"]

                status = {}
                for _ in range(40):
                    status_resp = await cli.get(f"/v1/runs/{run_id}")
                    status = await status_resp.json()
                    if status["status"] in {"completed", "failed", "cancelled"}:
                        break
                    await asyncio.sleep(0.05)
                assert status["status"] == "completed"

                events_resp = await asyncio.wait_for(
                    cli.get(f"/v1/runs/{run_id}/events"), timeout=10.0
                )
                assert events_resp.status == 200
                events = _parse_sse_events(await events_resp.text())

        assert [e["event"] for e in events] == [
            "tool.started",
            "message.delta",
            "message.delta",
            "tool.completed",
            "run.completed",
        ]
        assert [e["seq"] for e in events] == [1, 2, 3, 4, 5]
        for event in events:
            assert event["schema_version"] == 1
            assert event["event_id"] == f"{run_id}:{event['seq']}"
            assert event["run_id"] == run_id

        assert [e["delta"] for e in events if e["event"] == "message.delta"] == ["Hel", "lo"]
        assert events[0]["tool_call_id"] == "call_a"
        assert events[3]["tool_call_id"] == "call_a"
        assert events[3]["path"] == "a.py"
        assert events[4]["output"] == "Hello"
        assert events[4]["verification_state"] == "passed"
