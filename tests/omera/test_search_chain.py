import httpx
import pytest

from xavani_omera import search


@pytest.fixture(autouse=True)
def clean_cache():
    search.clear_search_cache()
    yield
    search.clear_search_cache()


def transport(codes: dict[str, int]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        code = codes.get(host, 200)
        if code != 200:
            return httpx.Response(code, json={"error": "nope"})
        if host == "api.tavily.com":
            return httpx.Response(200, json={"results": [{
                "title": "T", "url": "https://t.example/a",
                "content": "s", "raw_content": "body",
            }]})
        return httpx.Response(200, json={"results": [
            {"title": "D", "url": "https://d.example/b", "body": "s"},
        ]})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_first_available_backend_wins(monkeypatch):
    monkeypatch.setattr(search, "_ddgs_search",
                        lambda query, limit: [search.Hit("D", "https://d.example/b", "s")])
    async with httpx.AsyncClient(transport=transport({})) as client:
        hits, provider = await search.search_with_fallback(
            "q", 2, env={"TAVILY_API_KEY": "k", "RESEARCH_PROVIDER": "auto"},
            client=client)
    assert provider == "tavily"
    assert hits[0].url == "https://t.example/a"


@pytest.mark.asyncio
async def test_a_rate_limited_provider_falls_through(monkeypatch):
    monkeypatch.setattr(search, "_ddgs_search",
                        lambda query, limit: [search.Hit("D", "https://d.example/b", "s")])
    async with httpx.AsyncClient(transport=transport({"api.tavily.com": 429})) as client:
        hits, provider = await search.search_with_fallback(
            "q", 2,
            env={"TAVILY_API_KEY": "k", "RESEARCH_PROVIDER": "tavily,ddgs"},
            client=client)
    assert provider == "ddgs"
    assert hits[0].url == "https://d.example/b"


@pytest.mark.asyncio
async def test_the_cache_prevents_a_second_call(monkeypatch):
    calls = []

    def fake(query, limit):
        calls.append(1)
        return [search.Hit("D", "https://d.example/b", "s")]

    monkeypatch.setattr(search, "_ddgs_search", fake)
    async with httpx.AsyncClient(transport=transport({})) as client:
        await search.search_with_fallback(
            "q", 2, env={"RESEARCH_PROVIDER": "ddgs"}, client=client, now=100.0)
        await search.search_with_fallback(
            "q", 2, env={"RESEARCH_PROVIDER": "ddgs"}, client=client, now=200.0)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_the_cache_expires(monkeypatch):
    calls = []

    def fake(query, limit):
        calls.append(1)
        return [search.Hit("D", "https://d.example/b", "s")]

    monkeypatch.setattr(search, "_ddgs_search", fake)
    async with httpx.AsyncClient(transport=transport({})) as client:
        await search.search_with_fallback(
            "q", 2, env={"RESEARCH_PROVIDER": "ddgs"}, client=client, now=100.0)
        await search.search_with_fallback(
            "q", 2, env={"RESEARCH_PROVIDER": "ddgs"}, client=client,
            now=100.0 + search.CACHE_TTL_S + 1)
    assert len(calls) == 2


def test_no_backend_means_disabled():
    assert search.is_configured({"RESEARCH_PROVIDER": "nope"}) is False
    assert search.primary_provider({"RESEARCH_PROVIDER": "nope"}) == "none"
