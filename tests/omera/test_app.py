import json

import httpx
import pytest

from xavani_omera import app as app_module
from xavani_omera import keyless
from xavani_omera import inference
from xavani_omera.app import app
from xavani_omera.research import Hit, Page, ResearchResult

ENV = {
    "API_SERVER_KEY": "s" * 40,
    "INFERENCE_API_KEY": "k",
    "INFERENCE_MODEL": "model",
    "INFERENCE_FALLBACK_MODELS": "",
    "RESEARCH_PROVIDER": "nope",
    "JINA_READER": "off",
    "XAVANI_MODEL_NAME": "omera",
}
HEADERS = {"Authorization": "Bearer " + "s" * 40}


@pytest.fixture(autouse=True)
def reset_keyless_breaker():
    keyless.clear_keyless_breaker()
    yield
    keyless.clear_keyless_breaker()


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for key in ("TAVILY_API_KEY", "EXA_API_KEY", "API_SERVER_KEY_PREVIOUS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)


async def call(method, path, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_capabilities_match_the_contract():
    response = await call("GET", "/v1/capabilities", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["service"]["tools_enabled"] is False
    assert data["service"]["contract"] == 1
    assert data["service"]["research"]["server_side"] is True


@pytest.mark.asyncio
async def test_capabilities_require_auth():
    response = await call("GET", "/v1/capabilities")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_previous_key_is_accepted_during_rotation(monkeypatch):
    monkeypatch.setenv("API_SERVER_KEY_PREVIOUS", "p" * 40)
    response = await call("GET", "/v1/capabilities",
                          headers={"Authorization": "Bearer " + "p" * 40})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_shape_matches_the_omera_client(monkeypatch):
    async def fake_stream(messages, settings):
        yield "Hel"
        yield "lo"

    monkeypatch.setattr(inference, "stream", fake_stream)
    response = await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "stream": True,
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert response.status_code == 200
    assert response.headers["x-accel-buffering"] == "no"
    frames = [line for line in response.text.splitlines() if line.startswith("data: ")]
    assert frames[-1] == "data: [DONE]"
    body = json.loads(frames[0][6:])
    assert body["choices"][0]["delta"]["content"] == "Hel"
    final = json.loads(frames[-2][6:])
    assert final["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_non_stream_returns_complete_json(monkeypatch):
    async def fake_complete(messages, settings):
        return "Full answer"

    monkeypatch.setattr(inference, "complete", fake_complete)
    response = await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "messages": [{"role": "user", "content": "Hi"}],
    })
    data = response.json()
    assert data["choices"][0]["message"]["content"] == "Full answer"
    assert data["xavani"]["completed"] is True


@pytest.mark.asyncio
async def test_research_block_is_injected(monkeypatch):
    seen = {}

    async def fake_block(message, **kwargs):
        return "## Live web research (untrusted sources)\nBody"

    async def fake_complete(messages, settings):
        seen["messages"] = messages
        return "Answer"

    monkeypatch.setattr(app_module, "research_system_block", fake_block)
    monkeypatch.setattr(inference, "complete", fake_complete)
    await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "xavani_research": True,
        "messages": [{"role": "user", "content": "Latest CIPC deadline?"}],
    })
    assert "Live web research" in seen["messages"][0]["content"]


@pytest.mark.asyncio
async def test_unknown_root_field_is_rejected():
    response = await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "tools": [],
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_body_limit_is_enforced():
    response = await call("POST", "/v1/chat/completions", headers=HEADERS,
                          content=b"x" * 300_000)
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upstream_failure_is_a_clean_502(monkeypatch):
    async def fake_stream(messages, settings):
        raise inference.InferenceError("UPSTREAM_500")
        yield ""  # pragma: no cover

    monkeypatch.setattr(inference, "stream", fake_stream)
    response = await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "stream": True,
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert response.status_code == 502
    assert "UPSTREAM" not in response.text


@pytest.mark.asyncio
async def test_research_block_names_the_chain(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("RESEARCH_PROVIDER", "tavily,exa,ddgs")
    response = await call("GET", "/v1/capabilities", headers=HEADERS)
    research = response.json()["service"]["research"]
    assert research["provider"] == "tavily"
    assert research["providers"][0] == "tavily"
    assert research["returns_content"] is True
    assert research["cache_ttl_s"] == 900


def sample_result() -> ResearchResult:
    return ResearchResult(
        status="ok", provider="ddgs", query="cipc annual return", elapsed_ms=5,
        hits=[Hit("CIPC", "https://cipc.example/a", "Annual return.")],
        pages=[Page(
            "https://cipc.example/a", "CIPC",
            "Every company must file an annual return within 30 days of its "
            "anniversary date. The fee is R100 for a standard company.",
        )],
    )


@pytest.mark.asyncio
async def test_research_only_mode_answers_with_sources(monkeypatch):
    monkeypatch.delenv("INFERENCE_API_KEY", raising=False)
    monkeypatch.setenv("KEYLESS_MODEL", "off")

    async def fake_result(message, **kwargs):
        return sample_result()

    monkeypatch.setattr(app_module, "research_result_for", fake_result)
    response = await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "xavani_research": True,
        "messages": [{"role": "user", "content": "When is the CIPC annual return due?"}],
    })
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "Research mode" in content
    assert "https://cipc.example/a" in content


@pytest.mark.asyncio
async def test_research_only_mode_streams(monkeypatch):
    monkeypatch.delenv("INFERENCE_API_KEY", raising=False)
    monkeypatch.setenv("KEYLESS_MODEL", "off")

    async def fake_result(message, **kwargs):
        return sample_result()

    monkeypatch.setattr(app_module, "research_result_for", fake_result)
    response = await call("POST", "/v1/chat/completions", headers=HEADERS, json={
        "model": "omera", "stream": True, "xavani_research": True,
        "messages": [{"role": "user", "content": "When is the CIPC annual return due?"}],
    })
    assert response.status_code == 200
    assert "data: [DONE]" in response.text
    assert "Research mode" in response.text


@pytest.mark.asyncio
async def test_health_reports_the_mode(monkeypatch):
    monkeypatch.delenv("INFERENCE_API_KEY", raising=False)
    monkeypatch.setenv("KEYLESS_MODEL", "off")
    response = await call("GET", "/health")
    assert response.json()["mode"] == "research"


@pytest.mark.asyncio
async def test_health_reports_keyless_mode(monkeypatch):
    monkeypatch.delenv("INFERENCE_API_KEY", raising=False)
    monkeypatch.setenv("KEYLESS_MODEL", "on")
    response = await call("GET", "/health")
    assert response.json()["mode"] == "keyless"
