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
