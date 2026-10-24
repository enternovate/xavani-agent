"""OpenAI-compatible inference calls with ordered model fallbacks."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from xavani_omera.config import Settings

TIMEOUT = httpx.Timeout(45.0, connect=10.0)
ATTEMPTS_PER_MODEL = 2

logger = logging.getLogger(__name__)


class InferenceError(RuntimeError):
    """Every configured model failed."""


def _client() -> httpx.AsyncClient:
    """Build the HTTP client. Tests replace this function."""
    return httpx.AsyncClient(timeout=TIMEOUT)


def _models(settings: Settings) -> list[str]:
    models = [settings.inference_model]
    for item in (settings.inference_fallback_models or "").split(","):
        name = item.strip()
        if name and name not in models:
            models.append(name)
    return models


def _headers(settings: Settings) -> dict:
    return {
        "Authorization": f"Bearer {settings.inference_api_key}",
        "Content-Type": "application/json",
    }


def _payload(messages, settings: Settings, model: str, stream: bool) -> dict:
    return {
        "model": model,
        "messages": messages,
        "stream": stream,
        "max_tokens": settings.max_tokens,
    }


def _not_retryable(exc: Exception) -> bool:
    """A malformed request fails the same way on every model."""
    text = str(exc)
    return "UPSTREAM_4" in text and "UPSTREAM_429" not in text


async def _stream_one(messages, settings: Settings, model: str) -> AsyncIterator[str]:
    async with _client() as client:
        async with client.stream(
            "POST", f"{settings.inference_base_url}/chat/completions",
            json=_payload(messages, settings, model, True),
            headers=_headers(settings),
        ) as response:
            if response.status_code >= 400:
                await response.aread()
                raise InferenceError(f"UPSTREAM_{response.status_code}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or [{}]
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    yield delta


async def stream(messages, settings: Settings) -> AsyncIterator[str]:
    """Yield text deltas. Try each model twice before giving up."""
    last_error: Exception | None = None
    for model in _models(settings):
        for attempt in range(ATTEMPTS_PER_MODEL):
            emitted = False
            try:
                async for token in _stream_one(messages, settings, model):
                    emitted = True
                    yield token
                return
            except Exception as exc:
                last_error = exc
                if emitted:
                    raise
                logger.warning(
                    "inference_failed model=%s attempt=%d error=%s",
                    model, attempt + 1, type(exc).__name__,
                )
                if _not_retryable(exc):
                    raise
    raise last_error or InferenceError("NO_MODEL")


async def complete(messages, settings: Settings) -> str:
    """Return the full answer. Try each model twice before giving up."""
    last_error: Exception | None = None
    for model in _models(settings):
        for attempt in range(ATTEMPTS_PER_MODEL):
            try:
                async with _client() as client:
                    response = await client.post(
                        f"{settings.inference_base_url}/chat/completions",
                        json=_payload(messages, settings, model, False),
                        headers=_headers(settings),
                    )
                if response.status_code >= 400:
                    raise InferenceError(f"UPSTREAM_{response.status_code}")
                choices = response.json().get("choices") or [{}]
                content = (choices[0].get("message") or {}).get("content")
                if not isinstance(content, str) or not content.strip():
                    raise InferenceError("EMPTY_COMPLETION")
                return content
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "inference_failed model=%s attempt=%d error=%s",
                    model, attempt + 1, type(exc).__name__,
                )
                if _not_retryable(exc):
                    raise
    raise last_error or InferenceError("NO_MODEL")
