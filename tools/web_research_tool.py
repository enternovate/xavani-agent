"""Search the web and collect page text in one call."""
from __future__ import annotations

import json

from tools.registry import registry
from xavani_omera.research import format_context, is_research_configured, research

SCHEMA = {
    "name": "web_research",
    "description": (
        "Search the web and fetch the top pages. Returns titles, URLs, "
        "snippets, page text, and a ready-to-use source block."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "max_pages": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "How many pages to fetch (default 3)",
            },
        },
        "required": ["query"],
    },
}


def _check() -> bool:
    return is_research_configured()


async def web_research_tool(query: str, max_pages: int = 3) -> str:
    """Run research and return JSON for the model."""
    result = await research(query, max_pages=max(1, min(5, int(max_pages))))
    payload = {
        "success": result.status in {"ok", "empty"},
        "data": {
            "status": result.status,
            "provider": result.provider,
            "query": result.query,
            "elapsed_ms": result.elapsed_ms,
            "hits": [
                {"title": h.title, "url": h.url, "snippet": h.snippet}
                for h in result.hits
            ],
            "pages": [
                {"url": p.url, "title": p.title, "chars": len(p.text), "error": p.error}
                for p in result.pages
            ],
            "context": format_context(result) if result.status == "ok" else "",
        },
    }
    if result.status in {"failed", "disabled"}:
        payload["error"] = "WEB_RESEARCH_UNAVAILABLE"
    return json.dumps(payload)


registry.register(
    name="web_research",
    toolset="web",
    schema=SCHEMA,
    handler=lambda args, **kw: web_research_tool(
        args.get("query", ""), args.get("max_pages", 3),
    ),
    check_fn=_check,
    requires_env=[],
    is_async=True,
    emoji="🌐",
    max_result_size_chars=150_000,
)
