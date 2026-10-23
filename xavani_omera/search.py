"""Free web search backends in a ranked chain."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

TIMEOUT_S = 12.0
SNIPPET_CHARS = 300
CACHE_TTL_S = 900
CACHE_MAX = 64
DEFAULT_ORDER = ("tavily", "exa", "ddgs")


@dataclass(frozen=True)
class Hit:
    """One search result. Content holds page text when the provider returns it."""

    title: str
    url: str
    snippet: str
    content: str = ""


class SearchBackend(Protocol):
    name: str

    def available(self) -> bool: ...

    async def search(
        self, query: str, limit: int, client: httpx.AsyncClient,
    ) -> list[Hit]: ...


class TavilyBackend:
    """Tavily: 1,000 free credits per month, no card."""

    name = "tavily"

    def __init__(self, env=None) -> None:
        self._env = env if env is not None else os.environ

    @property
    def key(self) -> str:
        return (self._env.get("TAVILY_API_KEY") or "").strip()

    def available(self) -> bool:
        return bool(self.key)

    async def search(self, query, limit, client):
        response = await client.post(
            "https://api.tavily.com/search",
            headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "max_results": limit,
                "search_depth": "basic",
                "include_raw_content": True,
            },
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        hits: list[Hit] = []
        for item in (response.json().get("results") or [])[:limit]:
            url = (item.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            hits.append(Hit(
                title=(item.get("title") or url).strip()[:200],
                url=url,
                snippet=(item.get("content") or "").strip()[:SNIPPET_CHARS],
                content=(item.get("raw_content") or "").strip(),
            ))
        return hits


class ExaBackend:
    """Exa: $10 free credit, resets monthly, no card."""

    name = "exa"

    def __init__(self, env=None) -> None:
        self._env = env if env is not None else os.environ

    @property
    def key(self) -> str:
        return (self._env.get("EXA_API_KEY") or "").strip()

    def available(self) -> bool:
        return bool(self.key)

    async def search(self, query, limit, client):
        response = await client.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": self.key, "Content-Type": "application/json"},
            json={
                "query": query,
                "numResults": limit,
                "type": "auto",
                "contents": {"text": {"maxCharacters": 4000}},
            },
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        hits: list[Hit] = []
        for item in (response.json().get("results") or [])[:limit]:
            url = (item.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                continue
            text = (item.get("text") or "").strip()
            hits.append(Hit(
                title=(item.get("title") or url).strip()[:200],
                url=url,
                snippet=(item.get("summary") or text)[:SNIPPET_CHARS],
                content=text,
            ))
        return hits


class DdgsBackend:
    """DuckDuckGo scraping. No key, no card, weakest results."""

    name = "ddgs"

    def __init__(self, env=None) -> None:
        self._env = env if env is not None else os.environ

    def available(self) -> bool:
        try:
            import ddgs  # noqa: F401
        except ImportError:
            return False
        return True

    async def search(self, query, limit, client):
        return await asyncio.to_thread(_ddgs_search, query, limit)


BACKENDS = {"tavily": TavilyBackend, "exa": ExaBackend, "ddgs": DdgsBackend}


def _ddgs_search(query: str, limit: int) -> list[Hit]:
    from ddgs import DDGS

    hits: list[Hit] = []
    for item in DDGS().text(query, max_results=limit) or []:
        title = (item.get("title") or "").strip()
        url = (item.get("href") or item.get("url") or "").strip()
        if not title or not url.startswith(("http://", "https://")):
            continue
        hits.append(Hit(title, url, (item.get("body") or "").strip()[:SNIPPET_CHARS]))
    return hits


def backend_order(env=None) -> list[str]:
    """Return configured backend names in priority order."""
    resolved = env if env is not None else os.environ
    raw = (resolved.get("RESEARCH_PROVIDER") or "auto").strip().lower()
    if raw == "auto":
        names = DEFAULT_ORDER
    else:
        names = tuple(part.strip() for part in raw.split(",") if part.strip())
    ordered: list[str] = []
    for name in names:
        if name in BACKENDS and name not in ordered:
            ordered.append(name)
    return ordered


def available_backends(env=None) -> list[SearchBackend]:
    """Return instantiated backends that can run right now."""
    backends: list[SearchBackend] = []
    for name in backend_order(env):
        backend = BACKENDS[name](env)
        if backend.available():
            backends.append(backend)
    return backends


def is_configured(env=None) -> bool:
    """True when at least one backend can run."""
    return bool(available_backends(env))


def primary_provider(env=None) -> str:
    """Return the first available backend name, or none."""
    backends = available_backends(env)
    return backends[0].name if backends else "none"


_CACHE: dict[str, tuple[float, list[Hit], str]] = {}


def _key(query: str, limit: int) -> str:
    return f"{limit}:{query.strip().lower()}"


def clear_search_cache() -> None:
    _CACHE.clear()


def cached_hits(query: str, limit: int, now: float | None = None):
    entry = _CACHE.get(_key(query, limit))
    if entry is None:
        return None
    expires, hits, provider = entry
    if (now if now is not None else time.monotonic()) >= expires:
        _CACHE.pop(_key(query, limit), None)
        return None
    return hits, provider


def store_hits(query: str, limit: int, hits: list[Hit], provider: str,
               now: float | None = None) -> None:
    if len(_CACHE) >= CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[_key(query, limit)] = (
        (now if now is not None else time.monotonic()) + CACHE_TTL_S,
        hits,
        provider,
    )


async def search_with_fallback(
    query: str,
    limit: int,
    env=None,
    client: httpx.AsyncClient | None = None,
    now: float | None = None,
) -> tuple[list[Hit], str]:
    """Try each available backend in order. Return (hits, provider name)."""
    cached = cached_hits(query, limit, now)
    if cached is not None:
        return cached

    own_client = client is None
    client = client or httpx.AsyncClient()
    try:
        for backend in available_backends(env):
            try:
                hits = await backend.search(query, limit, client)
            except Exception as exc:
                logger.warning(
                    "search_failed provider=%s error=%s",
                    backend.name, type(exc).__name__,
                )
                continue
            if hits:
                store_hits(query, limit, hits, backend.name, now)
                logger.info("search_ok provider=%s hits=%d", backend.name, len(hits))
                return hits, backend.name
        return [], "none"
    finally:
        if own_client:
            await client.aclose()
