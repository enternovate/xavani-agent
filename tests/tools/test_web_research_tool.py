import json

import pytest

from tools import web_research_tool as module
from tools.registry import registry
from xavani_omera.research import Hit, Page, ResearchResult


def test_web_research_is_registered():
    entry = registry.get_entry("web_research")
    assert entry is not None
    assert entry.toolset == "web"
    assert entry.schema["name"] == "web_research"


@pytest.mark.asyncio
async def test_handler_returns_hits_and_context(monkeypatch):
    async def fake_research(query, **kwargs):
        return ResearchResult(
            status="ok", provider="tavily", query=query, elapsed_ms=5,
            hits=[Hit("CIPC", "https://cipc.example/a", "s")],
            pages=[Page("https://cipc.example/a", "CIPC", "Body")],
        )

    monkeypatch.setattr(module, "research", fake_research)
    data = json.loads(await module.web_research_tool("cipc annual return"))
    assert data["success"] is True
    assert data["data"]["hits"][0]["url"] == "https://cipc.example/a"
    assert data["data"]["context"]


@pytest.mark.asyncio
async def test_handler_reports_a_disabled_chain(monkeypatch):
    async def fake_research(query, **kwargs):
        return ResearchResult(status="disabled", provider="none", query=query)

    monkeypatch.setattr(module, "research", fake_research)
    data = json.loads(await module.web_research_tool("cipc"))
    assert data["success"] is False
    assert data["error"] == "WEB_RESEARCH_UNAVAILABLE"
