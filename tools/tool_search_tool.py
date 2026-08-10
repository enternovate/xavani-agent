#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""tool_search — search the deferred tool catalog.

Rarely-used tools are not wired into the default per-turn schema list (see
``model_tools.DEFERRED_TOOL_NAMES``). This meta-tool lets the agent discover
them by keyword so their schemas don't cost tokens on every turn. Returns a
JSON list of ``{"name", "description"}`` matches; follow with tool_describe
for the full schema, then tool_call to invoke.
"""

import json
import re

from tools.registry import registry, tool_error


def search_deferred_tools(query: str, limit: int = 8) -> str:
    """Search deferred tool names + descriptions; return matching tools."""
    if not query or not isinstance(query, str) or not query.strip():
        return tool_error("query is required")

    # The deferred set lives in model_tools; lazy-import to avoid a
    # circular import at module load (model_tools imports all tool files).
    from model_tools import DEFERRED_TOOL_NAMES

    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        limit = 8

    words = [w for w in re.split(r"\W+", query.strip().lower()) if w]
    if not words:
        return tool_error("query contains no searchable words")

    results = []
    for name in sorted(DEFERRED_TOOL_NAMES):
        entry = registry.get_entry(name)
        if entry is None:
            continue
        haystack = f"{name} {entry.description or ''}".lower()
        if all(w in haystack for w in words):
            results.append({"name": name, "description": entry.description or ""})
            if len(results) >= limit:
                break

    return json.dumps(
        {"query": query, "count": len(results), "results": results},
        ensure_ascii=False,
    )


# =============================================================================
# OpenAI Function-Calling Schema
# =============================================================================

TOOL_SEARCH_SCHEMA = {
    "name": "tool_search",
    "description": (
        "Search the deferred tool catalog — tools that exist but are not "
        "listed on the default wire to save tokens. Provide keywords for the "
        "capability you need; returns matching tool names and descriptions. "
        "Then use tool_describe to load a tool's full parameter schema, and "
        "tool_call to invoke it."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords describing the capability you need (e.g. 'generate image', 'discord').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return.",
                "default": 8,
            },
        },
        "required": ["query"],
    },
}


# --- Registry ---
registry.register(
    name="tool_search",
    toolset="tool_management",
    schema=TOOL_SEARCH_SCHEMA,
    handler=lambda args, **kw: search_deferred_tools(
        query=args.get("query", ""),
        limit=args.get("limit", 8),
    ),
    emoji="🔍",
)
