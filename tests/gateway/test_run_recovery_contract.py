# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Run-level cancellation and recovery contract (R1 Task 08).

A gateway run reaches a terminal state exactly once and never leaves work
half-executed behind it.  These tests drive the real ``/v1/runs`` handlers
(``gateway/platforms/api_server.py``) with a mock agent:

* POST /v1/runs/{run_id}/stop while the run is parked on a pending
  approval must release that approval WITHOUT approving it (the guarded
  command never runs) and end the run as ``cancelled``.
* A run whose turn fails must report the error and keep its session
  identity, emitting ``run.failed`` on both the pollable status and the
  event stream.

Overlapping coverage: ``tests/gateway/test_api_server_runs.py`` covers the
stop happy path (interrupt called, refs cleaned up) and
``tests/run_agent/test_concurrent_interrupt.py`` covers interrupt fan-out to
tool workers — neither pins the pending-approval release or the failed-run
terminal state.
"""

import asyncio
import threading
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import (
    APIServerAdapter,
    cors_middleware,
    security_headers_middleware,
)

# Dangerous (never hardline-blocked) command used to park a run on approval.
PROBE_COMMAND = "rm -rf /tmp/xavani-approval-probe"


# ---------------------------------------------------------------------------
# Helpers (mirrors tests/gateway/test_api_server_runs.py)
# ---------------------------------------------------------------------------


def _make_adapter(api_key: str = "") -> APIServerAdapter:
    extra = {}
    if api_key:
        extra["key"] = api_key
    return APIServerAdapter(PlatformConfig(enabled=True, extra=extra))


def _create_runs_app(adapter: APIServerAdapter) -> web.Application:
    mws = [mw for mw in (cors_middleware, security_headers_middleware) if mw is not None]
    app = web.Application(middlewares=mws)
    app["api_server_adapter"] = adapter
    app.router.add_post("/v1/runs", adapter._handle_runs)
    app.router.add_get("/v1/runs/{run_id}", adapter._handle_get_run)
    app.router.add_get("/v1/runs/{run_id}/events", adapter._handle_run_events)
    app.router.add_post("/v1/runs/{run_id}/approval", adapter._handle_run_approval)
    app.router.add_post("/v1/runs/{run_id}/stop", adapter._handle_stop_run)
    return app


def _make_agent(run_conversation):
    agent = MagicMock()
    agent.run_conversation.side_effect = run_conversation
    agent.interrupt = MagicMock()
    agent.session_prompt_tokens = 0
    agent.session_completion_tokens = 0
    agent.session_total_tokens = 0
    return agent


async def _poll_status(cli, run_id, wanted, attempts=120, delay=0.05):
    status = None
    for _ in range(attempts):
        status = await (await cli.get(f"/v1/runs/{run_id}")).json()
        if status["status"] in wanted:
            return status
        await asyncio.sleep(delay)
    raise AssertionError(f"run {run_id} never reached {wanted}; last={status}")


# ---------------------------------------------------------------------------
# Stop while an approval is pending
# ---------------------------------------------------------------------------


class TestStopDuringPendingApproval:
    @pytest.mark.asyncio
    async def test_pending_approval_is_released_unapproved_and_run_cancelled(self):
        """The agent thread is blocked inside the real gateway approval
        queue.  Stopping the run must tear the wait down as an UNRESOLVED
        (denied) request — the guarded command must never be approved — and
        the run must land in ``cancelled``."""
        from tools.approval import check_all_command_guards, has_blocking_approval

        adapter = _make_adapter()
        app = _create_runs_app(adapter)

        decisions = []
        approval_entered = threading.Event()
        agent_returned = threading.Event()

        def _blocked_run(user_message=None, conversation_history=None, task_id=None):
            approval_entered.set()
            decisions.append(check_all_command_guards(PROBE_COMMAND, "local"))
            agent_returned.set()
            return {"final_response": "unreachable", "messages": [], "api_calls": 1}

        mock_agent = _make_agent(_blocked_run)

        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent", return_value=mock_agent):
                resp = await cli.post("/v1/runs", json={"input": "clean up the workspace"})
                assert resp.status == 202
                run_id = (await resp.json())["run_id"]

                assert approval_entered.wait(timeout=5.0), "agent never reached the approval gate"
                status = await _poll_status(cli, run_id, {"waiting_for_approval"})
                assert status["last_event"] == "approval.request"

                approval_key = adapter._run_approval_sessions[run_id]
                assert has_blocking_approval(approval_key) is True, (
                    "expected a live pending approval for the run"
                )

                stop_resp = await cli.post(f"/v1/runs/{run_id}/stop")
                assert stop_resp.status == 200
                mock_agent.interrupt.assert_called_once_with("Stop requested via API")

                # The blocked approval was released — not approved.
                assert agent_returned.wait(timeout=5.0), "stop did not release the approval wait"
                assert decisions, "approval gate never returned"
                assert decisions[0]["approved"] is False, (
                    f"guarded command was approved on stop: {decisions[0]!r}"
                )
                assert "BLOCKED" in decisions[0]["message"]

                final = await _poll_status(cli, run_id, {"cancelled"})
                assert final["last_event"] == "run.cancelled"
                assert run_id not in adapter._active_run_agents
                assert run_id not in adapter._active_run_tasks
                assert run_id not in adapter._run_approval_sessions


# ---------------------------------------------------------------------------
# Failed run keeps its identity and reports the error
# ---------------------------------------------------------------------------


class TestFailedRunRecovery:
    @pytest.mark.asyncio
    async def test_failed_turn_reports_error_and_keeps_session_identity(self):
        """A turn that dies (provider error exhausted upstream) must surface
        the error on the run status AND the event stream, while the session
        identity it started with is preserved for a retry."""
        adapter = _make_adapter()
        app = _create_runs_app(adapter)

        transcript = [
            {"role": "user", "content": "do the thing"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_0"}]},
            {"role": "tool", "name": "read_file", "content": "ok", "tool_call_id": "call_0"},
        ]

        def _failed_run(user_message=None, conversation_history=None, task_id=None):
            return {
                "final_response": "API call failed after 3 retries: provider stalled",
                "messages": transcript,
                "api_calls": 3,
                "completed": False,
                "failed": True,
                "error": "provider stalled",
                "verification_state": "unverified",
            }

        mock_agent = _make_agent(_failed_run)

        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent", return_value=mock_agent):
                resp = await cli.post(
                    "/v1/runs",
                    json={"input": "do the thing", "session_id": "session-recovery"},
                )
                assert resp.status == 202
                run_id = (await resp.json())["run_id"]

                status = await _poll_status(cli, run_id, {"failed"})
                assert status["error"] == "provider stalled"
                assert status["last_event"] == "run.failed"
                assert status["session_id"] == "session-recovery", (
                    "failed run lost its session identity"
                )

                events_resp = await cli.get(f"/v1/runs/{run_id}/events")
                assert events_resp.status == 200
                body = await events_resp.text()
                assert "run.failed" in body
                assert "provider stalled" in body
                assert "run.completed" not in body

            # The run keeps the caller's session as the task id, so the next
            # run for the same session resumes the same conversation.
            assert mock_agent.run_conversation.call_args.kwargs["task_id"] == "session-recovery"
