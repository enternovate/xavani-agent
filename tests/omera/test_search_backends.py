import json

import httpx
import pytest

from xavani_omera.search import BingBackend, ExaBackend, TavilyBackend, backend_order


def test_order_defaults_to_the_ranked_chain():
    assert backend_order({}) == ["tavily", "exa", "ddgs", "bing"]


def test_order_respects_an_explicit_list():
    assert backend_order({"RESEARCH_PROVIDER": "ddgs,tavily"}) == ["ddgs", "tavily"]


def test_order_drops_unknown_names():
    assert backend_order({"RESEARCH_PROVIDER": "tavily,brave"}) == ["tavily"]


@pytest.mark.asyncio
async def test_tavily_sends_the_documented_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"results": [{
            "title": "CIPC", "url": "https://cipc.example/a",
            "content": "Annual return.", "raw_content": "Full page text.",
        }]})

    backend = TavilyBackend({"TAVILY_API_KEY": "tvly-test"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        hits = await backend.search("cipc", 2, client)

    assert seen["url"] == "https://api.tavily.com/search"
    assert seen["auth"] == "Bearer tvly-test"
    body = json.loads(seen["body"])
    assert body["include_raw_content"] is True
    assert body["search_depth"] == "basic"
    assert hits[0].url == "https://cipc.example/a"
    assert hits[0].content == "Full page text."


@pytest.mark.asyncio
async def test_exa_sends_the_documented_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["x-api-key"]
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"results": [{
            "title": "SARS", "url": "https://sars.example/b", "text": "Tax dates.",
        }]})

    backend = ExaBackend({"EXA_API_KEY": "exa-test"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        hits = await backend.search("sars", 2, client)

    assert seen["url"] == "https://api.exa.ai/search"
    assert seen["key"] == "exa-test"
    body = json.loads(seen["body"])
    assert body["numResults"] == 2
    assert hits[0].content == "Tax dates."


def test_a_backend_without_a_key_is_unavailable():
    assert TavilyBackend({}).available() is False
    assert ExaBackend({}).available() is False
    assert TavilyBackend({"TAVILY_API_KEY": "k"}).available() is True


RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item><title>CIPC &amp; returns</title><link>https://cipc.example/a</link>
<description>File &lt;b&gt;within&lt;/b&gt; 30 days.</description></item>
</channel></rss>"""


@pytest.mark.asyncio
async def test_bing_parses_rss_without_a_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.bing.com"
        assert request.url.params["format"] == "rss"
        return httpx.Response(200, text=RSS)

    backend = BingBackend({})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        hits = await backend.search("cipc", 3, client)

    assert hits[0].title == "CIPC & returns"
    assert hits[0].url == "https://cipc.example/a"
    assert hits[0].snippet == "File within 30 days."
