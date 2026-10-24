"""Build the Omera research block for one user message."""
from __future__ import annotations

import asyncio
import logging
import os

from xavani_omera.research import (
    DEFAULT_BUDGET_MS,
    DEFAULT_MAX_PAGES,
    ResearchResult,
    build_query,
    format_context,
    is_research_configured,
    research,
    should_research,
)

logger = logging.getLogger(__name__)


async def research_result_for(
    user_message,
    *,
    env=None,
    max_pages: int | None = None,
    budget_ms: int | None = None,
) -> ResearchResult | None:
    """Return a research result, or None when research is off or unneeded."""
    if not isinstance(user_message, str):
        return None
    resolved = env if env is not None else os.environ
    if not is_research_configured(resolved):
        return None
    if not should_research(user_message):
        return None

    pages = max_pages or int(resolved.get("RESEARCH_MAX_PAGES", DEFAULT_MAX_PAGES))
    budget = budget_ms or int(resolved.get("RESEARCH_BUDGET_MS", DEFAULT_BUDGET_MS))
    try:
        result = await asyncio.wait_for(
            research(
                build_query(user_message),
                max_pages=pages,
                budget_ms=budget,
                env=resolved,
            ),
            timeout=budget / 1000 + 8.0,
        )
    except Exception as exc:
        logger.info("omera_research outcome=error error=%s", type(exc).__name__)
        return None
    if result.status != "ok":
        logger.info("omera_research outcome=%s provider=%s",
                    result.status, result.provider)
        return None
    logger.info(
        "omera_research outcome=ok provider=%s pages=%d ms=%d",
        result.provider, len([p for p in result.pages if p.text]), result.elapsed_ms,
    )
    return result


async def research_system_block(
    user_message,
    *,
    env=None,
    max_pages: int | None = None,
    budget_ms: int | None = None,
) -> str | None:
    """Return a formatted system block, or None when research is off."""
    result = await research_result_for(
        user_message, env=env, max_pages=max_pages, budget_ms=budget_ms,
    )
    return format_context(result) if result is not None else None
