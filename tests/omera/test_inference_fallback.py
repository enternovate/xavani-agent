import json

import httpx
import pytest

from xavani_omera import inference
from xavani_omera.config import Settings

PRIMARY = "primary/model"
BACKUP = "backup/model"


def settings(**overrides) -> Settings:
    values = dict(
        api_key="s" * 40,
        model_name="omera",
        inference_base_url="https://model.invalid/v1",
        inference_api_key="k",
        inference_model=PRIMARY,
        inference_fallback_models=BACKUP,
        max_tokens=512,
    )
    values.update(overrides)
    return Settings(**values)


def transport(status: dict[str, int], stream: bool = True) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        code = status.get(body["model"], 200)
        if code != 200:
            return httpx.Response(code, json={"error": "nope"})
        if body.get("stream"):
            frames = (
                'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n'
                "data: [DONE]\n\n"
            )
            return httpx.Response(
                200, text=frames, headers={"content-type": "text/event-stream"}
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "Full"}}]})

    return httpx.MockTransport(handler)


def use(monkeypatch, mock: httpx.MockTransport) -> None:
    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=mock)

    monkeypatch.setattr(inference, "_client", factory)


@pytest.mark.asyncio
async def test_stream_falls_back_when_the_primary_is_rate_limited(monkeypatch):
    use(monkeypatch, transport({PRIMARY: 429}))
    tokens = [token async for token in inference.stream([], settings())]
    assert "".join(tokens) == "Hi"


@pytest.mark.asyncio
async def test_stream_tries_each_model_twice(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(503, json={"error": "nope"})

    monkeypatch.setattr(
        inference, "_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(inference.InferenceError):
        [token async for token in inference.stream([], settings())]
    assert calls == [PRIMARY, PRIMARY, BACKUP, BACKUP]


@pytest.mark.asyncio
async def test_complete_uses_the_fallback(monkeypatch):
    use(monkeypatch, transport({PRIMARY: 500}, stream=False))
    assert await inference.complete([], settings()) == "Full"


@pytest.mark.asyncio
async def test_a_400_does_not_retry(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(400, json={"error": "bad request"})

    monkeypatch.setattr(
        inference, "_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(inference.InferenceError):
        [token async for token in inference.stream([], settings())]
    assert calls == [PRIMARY]
