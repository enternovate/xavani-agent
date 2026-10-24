import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from gateway.config import PlatformConfig
from gateway.platforms import api_server as api

SERVICE_KEY = "unit-service-key-with-32-characters-minimum"


@asynccontextmanager
async def restricted_client(monkeypatch, block):
    adapter = api.APIServerAdapter(PlatformConfig(enabled=True, extra={
        "key": SERVICE_KEY, "host": "127.0.0.1", "port": 0,
        "model_name": "omera", "omera_mode": True,
    }))
    adapter._run_agent = AsyncMock(return_value=({
        "final_response": "Answer", "completed": True,
        "partial": False, "failed": False,
    }, {}))
    monkeypatch.setattr(api, "research_system_block", block)
    try:
        assert await adapter.connect() is True
        port = adapter._site._server.sockets[0].getsockname()[1]
        async with ClientSession(
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


def body(research: bool):
    return {
        "model": "omera", "stream": False, "xavani_research": research,
        "messages": [
            {"role": "system", "content": "You are Omera."},
            {"role": "user", "content": "Latest CIPC deadline?"},
        ],
    }


@pytest.mark.asyncio
async def test_research_block_reaches_the_system_prompt(monkeypatch):
    async def fake_block(message, **kwargs):
        return "## Live web research (untrusted sources)\nBody"

    async with restricted_client(monkeypatch, fake_block) as (client, adapter):
        response = await client.post("/v1/chat/completions", json=body(True))
        assert response.status == 200

    prompt = adapter._run_agent.call_args.kwargs["ephemeral_system_prompt"]
    assert "Live web research" in prompt


@pytest.mark.asyncio
async def test_research_off_skips_the_call(monkeypatch):
    calls = []

    async def fake_block(message, **kwargs):
        calls.append(message)
        return "block"

    async with restricted_client(monkeypatch, fake_block) as (client, adapter):
        response = await client.post("/v1/chat/completions", json=body(False))
        assert response.status == 200

    assert calls == []


@pytest.mark.asyncio
async def test_research_failure_never_breaks_the_reply(monkeypatch):
    async def fake_block(message, **kwargs):
        raise RuntimeError("search exploded")

    async with restricted_client(monkeypatch, fake_block) as (client, adapter):
        response = await client.post("/v1/chat/completions", json=body(True))
        assert response.status == 200
        payload = await response.json()
        assert payload["choices"][0]["message"]["content"] == "Answer"
