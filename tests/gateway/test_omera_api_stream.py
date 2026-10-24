import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms import api_server as api


@pytest.mark.asyncio
@pytest.mark.parametrize("result,expected", [
    ({"completed": True, "partial": False, "failed": False}, "stop"),
    ({"completed": False, "failed": True}, "error"),
    ({"completed": True, "partial": True}, "length"),
    ({"final_response": "No completion evidence."}, "error"),
    (RuntimeError("SYNTHETIC_PRIVATE_STREAM_MARKER"), "error"),
])
async def test_omera_stream_requires_actual_completion(result, expected, caplog):
    adapter = api.APIServerAdapter(PlatformConfig(enabled=True, extra={
        "key": "unit-service-key", "model_name": "omera", "omera_mode": True,
    }))

    async def run(**kwargs):
        kwargs["stream_delta_callback"]("Response text")
        if isinstance(result, Exception):
            raise result
        return result, {}

    adapter._run_agent = run
    app = web.Application()
    app.router.add_post("/v1/chat/completions", adapter._handle_chat_completions)
    try:
        async with TestClient(TestServer(app)) as client:
            response = await client.post("/v1/chat/completions", headers={
                "Authorization": "Bearer unit-service-key",
            }, json={
                "model": "omera", "stream": True,
                "messages": [{"role": "user", "content": "Hello"}],
            })
            text = await response.text()
            frames = [json.loads(line[6:]) for line in text.splitlines()
                      if line.startswith("data: ") and line != "data: [DONE]"]
            assert frames[-1]["choices"][0]["finish_reason"] == expected
            assert "SYNTHETIC_PRIVATE_STREAM_MARKER" not in text
            assert "SYNTHETIC_PRIVATE_STREAM_MARKER" not in caplog.text
    finally:
        adapter._response_store.close()
