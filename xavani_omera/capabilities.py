"""Capability payloads shared by both Omera entry points."""
from __future__ import annotations

import os

from xavani_omera.research import DEFAULT_MAX_PAGES, jina_enabled
from xavani_omera.search import CACHE_TTL_S, available_backends


def research_capabilities(env=None) -> dict:
    """Describe the server-side research feature."""
    resolved = env if env is not None else os.environ
    backends = available_backends(resolved)
    names = [backend.name for backend in backends]
    try:
        max_pages = int(resolved.get("RESEARCH_MAX_PAGES", DEFAULT_MAX_PAGES))
    except ValueError:
        max_pages = DEFAULT_MAX_PAGES
    return {
        "enabled": bool(names),
        "provider": names[0] if names else "none",
        "providers": names,
        "server_side": True,
        "fetches_pages": True,
        "returns_content": any(name in {"tavily", "exa"} for name in names),
        "jina_fallback": jina_enabled(resolved),
        "cache_ttl_s": CACHE_TTL_S,
        "max_pages": max_pages,
    }


def omera_service_payload(model_name: str, env=None) -> dict:
    """Return the contract object. Keep every existing field unchanged."""
    return {
        "model": model_name,
        "auth": {"type": "bearer", "required": True},
        "service": {
            "name": "omera",
            "contract": 1,
            "stateless_requests": True,
            "tools_enabled": False,
            "memory_enabled": False,
            "context_files_enabled": False,
            "transcript_persistence": False,
            "research": research_capabilities(env),
        },
    }
