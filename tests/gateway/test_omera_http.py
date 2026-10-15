import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import aiohttp
import pytest

from gateway.config import PlatformConfig
from gateway.platforms import api_server as api

SERVICE_KEY = "unit-service-key-with-32-characters-minimum"


def chat_body():
    return {
        "model": "omera", "stream": False,
        "messages": [
            {"role": "system", "content": "Business rules."},
            {"role": "user", "content": "Help me obtain my first customer."},
        ],
    }


@asynccontextmanager
async def restricted_client():
    adapter = api.APIServerAdapter(PlatformConfig(enabled=True, extra={
        "key": SERVICE_KEY, "host": "127.0.0.1", "port": 0,
        "model_name": "omera", "omera_mode": True,
    }))
    adapter._run_agent = AsyncMock(return_value=({
        "final_response": "Speak to 5 potential customers.",
        "completed": True, "partial": False, "failed": False,
    }, {}))
    try:
        assert await adapter.connect() is True
        port = adapter._site._server.sockets[0].getsockname()[1]
        async with aiohttp.ClientSession(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": f"Bearer {SERVICE_KEY}"},
        ) as client:
            yield client, adapter
    finally:
        await adapter.disconnect()
        tasks = tuple(adapter._background_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        adapter._response_store.close()


@pytest.mark.asyncio
async def test_restricted_chat_enforces_chunked_body_limit():
    async def chunks():
        for _ in range(17):
            yield b"x" * 16000

    async with restricted_client() as (client, adapter):
        response = await client.post(
            "/v1/chat/completions", data=chunks(),
            headers={"Content-Type": "application/json"},
        )
        assert response.status == 413
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"tools": []}, {"model": "other"}, {"stream": "false"},
    {"messages": []}, {"messages": ["not-a-message"]},
])
async def test_restricted_chat_rejects_invalid_request(change):
    async with restricted_client() as (client, adapter):
        response = await client.post(
            "/v1/chat/completions", json={**chat_body(), **change},
        )
        assert response.status == 400
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("index,key,value", [
    (0, "role", "user"),
    (1, "role", "system"),
    (1, "role", "assistant"),
    (1, "role", []),
    (1, "role", {"unexpected": "role"}),
    (1, "content", []),
    (1, "content", {"type": "text", "text": "nested"}),
    (1, "content", ""),
    (1, "content", "   "),
])
async def test_restricted_chat_rejects_invalid_message_values(index, key, value):
    body = chat_body()
    body["messages"][index][key] = value
    async with restricted_client() as (client, adapter):
        response = await client.post("/v1/chat/completions", json=body)
        assert response.status == 400
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
async def test_restricted_chat_rejects_unknown_message_fields():
    body = chat_body()
    body["messages"][1]["tool_calls"] = []
    async with restricted_client() as (client, adapter):
        response = await client.post("/v1/chat/completions", json=body)
        assert response.status == 400
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [[], None, "invalid-root"])
async def test_restricted_chat_rejects_invalid_roots(body):
    async with restricted_client() as (client, adapter):
        response = await client.post("/v1/chat/completions", json=body)
        assert response.status == 400
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", [
    "X-Xavani-Session-Id", "X-Xavani-Session-Key", "Idempotency-Key",
])
@pytest.mark.parametrize("value", ["caller-state", ""])
async def test_restricted_requests_reject_state_headers(name, value):
    async with restricted_client() as (client, adapter):
        response = await client.post(
            "/v1/chat/completions", json=chat_body(), headers={name: value},
        )
        assert response.status == 403
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", "/health/detailed"),
    ("GET", "/v1/profiles"),
    ("GET", "/v1/profiles/active"),
    ("GET", "/v1/skills"),
    ("GET", "/api/jobs"),
    ("POST", "/api/jobs"),
    ("POST", "/v1/responses"),
    ("POST", "/v1/runs"),
])
async def test_restricted_routes_deny_general_operations(method, path):
    async with restricted_client() as (client, adapter):
        response = await client.request(method, path, json={})
        assert response.status == 404
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/health", "/v1/models", "/v1/capabilities"])
async def test_restricted_routes_require_auth(path):
    async with restricted_client() as (client, adapter):
        response = await client.get(path, headers={"Authorization": ""})
        assert response.status == 401
        adapter._run_agent.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["", "change-me"])
async def test_restricted_start_rejects_missing_or_placeholder_key(key):
    adapter = api.APIServerAdapter(PlatformConfig(enabled=True, extra={
        "key": key, "port": 0, "omera_mode": True, "model_name": "omera",
    }))
    before = set(adapter._background_tasks)
    try:
        assert await adapter.connect() is False
        assert adapter._app is None
        assert set(adapter._background_tasks) == before
    finally:
        await adapter.disconnect()
        adapter._response_store.close()
