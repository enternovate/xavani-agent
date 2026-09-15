# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for host verification state surfacing on the /v1/runs API.

The agent loop returns ``verification_state``, ``missing_checks`` and
``failed_checks`` in the run result dict. These tests assert the gateway
surfaces them on both the pollable run status and the SSE lifecycle
events, and that legacy result dicts without the keys degrade safely.
"""

import asyncio
import json
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


def _make_adapter(api_key: str = "") -> APIServerAdapter:
    extra = {}
    if api_key:
        extra["key"] = api_key
    config = PlatformConfig(enabled=True, extra=extra)
    return APIServerAdapter(config)


def _create_runs_app(adapter: APIServerAdapter) -> web.Application:
    mws = [mw for mw in (cors_middleware, security_headers_middleware) if mw is not None]
    app = web.Application(middlewares=mws)
    app["api_server_adapter"] = adapter
    app.router.add_post("/v1/runs", adapter._handle_runs)
    app.router.add_get("/v1/runs/{run_id}", adapter._handle_get_run)
    app.router.add_get("/v1/runs/{run_id}/events", adapter._handle_run_events)
    app.router.add_post("/v1/runs/{run_id}/stop", adapter._handle_stop_run)
    return app


def _make_result_agent(result: dict) -> MagicMock:
    agent = MagicMock()
    agent.run_conversation.return_value = result
    agent.session_prompt_tokens = 0
    agent.session_completion_tokens = 0
    agent.session_total_tokens = 0
    return agent


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


async def _await_terminal_status(cli, run_id: str) -> dict:
    status = {}
    for _ in range(40):
        status_resp = await cli.get(f"/v1/runs/{run_id}")
        assert status_resp.status == 200
        status = await status_resp.json()
        if status["status"] in {"completed", "failed", "cancelled"}:
            return status
        await asyncio.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached a terminal status: {status}")


async def _collect_events_until(cli, run_id: str, event_name: str) -> dict:
    events_resp = await asyncio.wait_for(
        cli.get(f"/v1/runs/{run_id}/events"), timeout=10.0
    )
    assert events_resp.status == 200
    body = await events_resp.text()
    events = _parse_sse_events(body)
    for event in events:
        if event.get("event") == event_name:
            return event
    raise AssertionError(f"no {event_name} event in stream: {events}")


@pytest.fixture
def adapter():
    return _make_adapter()


class TestRunVerificationStateStatus:
    @pytest.mark.asyncio
    async def test_completed_run_status_includes_passed_state(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "final_response": "done",
                    "verification_state": "passed",
                    "missing_checks": [],
                    "failed_checks": [],
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                assert resp.status == 202
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)

                assert status["status"] == "completed"
                assert status["verification_state"] == "passed"
                assert status["missing_checks"] == []
                assert status["failed_checks"] == []

    @pytest.mark.asyncio
    async def test_completed_run_status_passes_failed_lists_through(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "final_response": "done",
                    "verification_state": "failed",
                    "missing_checks": ["lint"],
                    "failed_checks": ["unit", "integration"],
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)

                assert status["status"] == "completed"
                assert status["verification_state"] == "failed"
                assert status["missing_checks"] == ["lint"]
                assert status["failed_checks"] == ["unit", "integration"]

    @pytest.mark.asyncio
    async def test_legacy_result_without_fields_reports_not_required(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({"final_response": "done"})

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)

                assert status["status"] == "completed"
                assert status["output"] == "done"
                assert status["verification_state"] == "not_required"
                assert status["missing_checks"] == []
                assert status["failed_checks"] == []

    @pytest.mark.asyncio
    async def test_structured_failure_status_reports_unverified(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "failed": True,
                    "error": "x",
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)

                assert status["status"] == "failed"
                assert status["error"] == "x"
                assert status["verification_state"] == "unverified"

    @pytest.mark.asyncio
    async def test_exception_failure_status_reports_unverified(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                agent = MagicMock()
                agent.run_conversation.side_effect = RuntimeError("boom")
                agent.session_prompt_tokens = 0
                agent.session_completion_tokens = 0
                agent.session_total_tokens = 0
                mock_create.return_value = agent

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)

                assert status["status"] == "failed"
                assert status["error"] == "boom"
                assert status["verification_state"] == "unverified"


class TestRunVerificationStateEvents:
    @pytest.mark.asyncio
    async def test_completed_event_carries_verification_fields(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "final_response": "Hello!",
                    "verification_state": "passed",
                    "missing_checks": [],
                    "failed_checks": [],
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                event = await _collect_events_until(cli, run_id, "run.completed")

                assert event["output"] == "Hello!"
                assert event["verification_state"] == "passed"
                assert event["missing_checks"] == []
                assert event["failed_checks"] == []

    @pytest.mark.asyncio
    async def test_completed_event_passes_failed_lists_through(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "final_response": "done",
                    "verification_state": "failed",
                    "missing_checks": ["lint"],
                    "failed_checks": ["unit"],
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                event = await _collect_events_until(cli, run_id, "run.completed")

                assert event["verification_state"] == "failed"
                assert event["missing_checks"] == ["lint"]
                assert event["failed_checks"] == ["unit"]

    @pytest.mark.asyncio
    async def test_legacy_result_event_defaults_safely(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({"final_response": "done"})

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                event = await _collect_events_until(cli, run_id, "run.completed")

                assert event["verification_state"] == "not_required"
                assert event["missing_checks"] == []
                assert event["failed_checks"] == []

    @pytest.mark.asyncio
    async def test_failed_event_carries_unverified_state(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "failed": True,
                    "error": "x",
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                event = await _collect_events_until(cli, run_id, "run.failed")

                assert event["error"] == "x"
                assert event["verification_state"] == "unverified"


    @pytest.mark.asyncio
    async def test_structured_failure_carries_check_lists_on_status_and_event(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                mock_create.return_value = _make_result_agent({
                    "failed": True,
                    "error": "x",
                    "verification_state": "blocked",
                    "missing_checks": ["unit"],
                    "failed_checks": ["lint"],
                })

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)
                assert status["status"] == "failed"
                assert status["verification_state"] == "blocked"
                assert status["missing_checks"] == ["unit"]
                assert status["failed_checks"] == ["lint"]

                event = await _collect_events_until(cli, run_id, "run.failed")
                assert event["verification_state"] == "blocked"
                assert event["missing_checks"] == ["unit"]
                assert event["failed_checks"] == ["lint"]

    @pytest.mark.asyncio
    async def test_exception_failure_defaults_check_lists(self, adapter):
        app = _create_runs_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch.object(adapter, "_create_agent") as mock_create:
                agent = MagicMock()
                agent.run_conversation.side_effect = RuntimeError("boom")
                agent.session_prompt_tokens = 0
                agent.session_completion_tokens = 0
                agent.session_total_tokens = 0
                mock_create.return_value = agent

                resp = await cli.post("/v1/runs", json={"input": "hello"})
                run_id = (await resp.json())["run_id"]

                status = await _await_terminal_status(cli, run_id)
                assert status["verification_state"] == "unverified"
                assert status["missing_checks"] == []
                assert status["failed_checks"] == []

                event = await _collect_events_until(cli, run_id, "run.failed")
                assert event["missing_checks"] == []
                assert event["failed_checks"] == []
