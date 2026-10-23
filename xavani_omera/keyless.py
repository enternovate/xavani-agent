"""Keyless operation: a no-key model endpoint and an extractive fallback."""
from __future__ import annotations

import logging
import os
import re
import time

import httpx

from xavani_omera.research import ResearchResult, format_context

logger = logging.getLogger(__name__)

DEFAULT_MODEL_URL = "https://text.pollinations.ai/openai"
DEFAULT_MODEL_NAME = "openai"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_ANSWER_CHARS = 1800
MAX_SENTENCES = 5
MAX_CONTEXT_CHARS = 3000
BREAKER_S = 120.0

MODE_LABEL = (
    "Research mode. This answer is assembled from live sources and cites them. "
    "Add a model key for conversational replies."
)

SYSTEM_PROMPT = (
    "You are Omera, a practical South African business advisor. "
    "Answer with concrete steps, costs in rand, and a next action. "
    "Use the live web research when it is present, and cite source URLs."
)

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "what", "when",
    "where", "which", "how", "does", "did", "are", "was", "were", "can",
    "could", "should", "would", "about", "into", "your", "you", "our",
    "their", "they", "them", "have", "has", "had", "not", "but", "all",
    "any", "one", "get", "got", "make", "made", "need", "want", "will",
}

BOILERPLATE = re.compile(
    r"cookie|privacy policy|subscribe|newsletter|javascript|all rights reserved|"
    r"sign in|log in|enable javascript|browser does not support",
    re.I,
)


def _env(env):
    return env if env is not None else os.environ


_down_until = 0.0


def _is_down() -> bool:
    return time.monotonic() < _down_until


def clear_keyless_breaker() -> None:
    """Tests only."""
    global _down_until
    _down_until = 0.0


def model_enabled(env=None) -> bool:
    """True when the keyless model endpoint is explicitly enabled."""
    resolved = _env(env)
    return (resolved.get("KEYLESS_MODEL") or "off").strip().lower() == "on"


def _client() -> httpx.AsyncClient:
    """Build the HTTP client. Tests replace this function."""
    return httpx.AsyncClient(timeout=TIMEOUT)


async def model_complete(messages, env=None) -> str:
    """Call the keyless OpenAI-compatible endpoint."""
    resolved = _env(env)
    url = (resolved.get("KEYLESS_MODEL_URL") or DEFAULT_MODEL_URL).strip()
    model = (resolved.get("KEYLESS_MODEL_NAME") or DEFAULT_MODEL_NAME).strip()
    async with _client() as client:
        response = await client.post(url, json={
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": 900,
        })
    if response.status_code >= 400:
        raise RuntimeError(f"KEYLESS_{response.status_code}")
    choices = response.json().get("choices") or [{}]
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("KEYLESS_EMPTY")
    return content.strip()


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", (text or "").lower())
        if token not in STOPWORDS
    }


def _score(sentence: str, tokens: set[str], position: int) -> float:
    words = _tokens(sentence)
    overlap = len(tokens & words)
    density = overlap / max(1, len(words))
    dated = 1 if re.search(r"\b(19|20)\d{2}\b|\bR\s?\d", sentence) else 0
    definition = 1 if re.search(
        r"\b(is|are|means|stands for|refers to|defined as)\b", sentence, re.I,
    ) else 0
    return overlap * 2 + density * 3 + dated + definition - position * 0.05


def compose_research_answer(
    user_message: str,
    result: ResearchResult | None,
    max_sentences: int = MAX_SENTENCES,
) -> str:
    """Build a cited answer from fetched pages, with no model."""
    if result is None or result.status != "ok":
        return MODE_LABEL + "\n\nNo live sources were reachable for this question."

    tokens = _tokens(user_message)
    candidates: list[tuple[float, str, str]] = []
    for page in result.pages:
        if not page.text:
            continue
        for position, raw in enumerate(re.split(r"(?<=[.!?])\s+", page.text)):
            sentence = " ".join(raw.split())
            if not 40 <= len(sentence) <= 320:
                continue
            if BOILERPLATE.search(sentence):
                continue
            candidates.append((_score(sentence, tokens, position), sentence, page.url))

    if not candidates:
        for hit in result.hits[:max_sentences]:
            snippet = " ".join((hit.snippet or "").split())
            if snippet:
                candidates.append((1.0, snippet, hit.url))

    candidates.sort(key=lambda item: item[0], reverse=True)

    picked: list[tuple[str, str]] = []
    seen: set[str] = set()
    for _, sentence, url in candidates:
        key = re.sub(r"\W+", "", sentence.lower())[:60]
        if key in seen:
            continue
        seen.add(key)
        picked.append((sentence, url))
        if len(picked) >= max_sentences:
            break

    if not picked:
        return MODE_LABEL + "\n\nNo live sources were reachable for this question."

    titles = {hit.url: hit.title for hit in result.hits}
    order: list[str] = []
    lines: list[str] = []
    for sentence, url in picked:
        if url not in order:
            order.append(url)
        lines.append(f"- {sentence} [{order.index(url) + 1}]")

    sources = "\n".join(
        f"[{index}] {titles.get(url) or url} — {url}"
        for index, url in enumerate(order, start=1)
    )
    header = MODE_LABEL + "\n\n"
    footer = "\n\nSources:\n" + sources
    budget = MAX_ANSWER_CHARS - len(header) - len(footer)
    kept: list[str] = []
    for line in lines:
        if len("\n".join(kept + [line])) > budget:
            break
        kept.append(line)
    if not kept:
        kept = lines[:1]
    return header + "\n".join(kept) + footer


def build_messages(user_message: str, result: ResearchResult | None,
                   system_prompt: str | None = None) -> list[dict]:
    """Assemble the model request, with research when it exists."""
    system = SYSTEM_PROMPT
    if system_prompt:
        system = f"{system_prompt}\n\n{system}"
    if result is not None and result.status == "ok":
        system = system + "\n\n" + format_context(result)[:MAX_CONTEXT_CHARS]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]


async def answer(user_message: str, result: ResearchResult | None, env=None,
                 system_prompt: str | None = None) -> str:
    """Use the keyless model when it answers, else compose from sources."""
    global _down_until
    if model_enabled(env) and not _is_down():
        try:
            text = await model_complete(
                build_messages(user_message, result, system_prompt), env,
            )
            _down_until = 0.0
            return text
        except Exception as exc:
            _down_until = time.monotonic() + BREAKER_S
            logger.info("keyless_model_failed error=%s", type(exc).__name__)
    return compose_research_answer(user_message, result)


def mode_for(env=None) -> str:
    """Return model, keyless, or research."""
    resolved = _env(env)
    if (resolved.get("INFERENCE_API_KEY") or "").strip() and (
        resolved.get("INFERENCE_MODEL") or ""
    ).strip():
        return "model"
    if model_enabled(resolved) and not _is_down():
        return "keyless"
    return "research"
