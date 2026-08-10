#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""tool_describe — load the full JSON schema of a single tool.

Deferred tools are not wired into the default per-turn schema list, so the
model cannot see their parameters. This meta-tool returns a tool's complete
registered schema on demand. Use after tool_search, before tool_call.
"""

import json

from tools.registry import registry, tool_error


def describe_tool(name: str) -> str:
    """Return the full registered JSON schema for *name*, or an error."""
    if not name or not isinstance(name, str):
        return tool_error("name is required")

    entry = registry.get_entry(name)
    if entry is None:
        return tool_error(f"Unknown tool: {name}")

    schema = dict(entry.schema)
    # Ensure the schema always carries its name (mirrors registry behavior).
    schema.setdefault("name", entry.name)
    return json.dumps(schema, ensure_ascii=False)


# =============================================================================
# OpenAI Function-Calling Schema
# =============================================================================

TOOL_DESCRIBE_SCHEMA = {
    "name": "tool_describe",
    "description": (
        "Load the full JSON parameter schema for one tool, including tools "
        "not listed on the default wire. Use after tool_search returns a "
        "matching tool name, and before tool_call so you pass arguments that "
        "match the tool's schema."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Exact tool name as returned by tool_search.",
            },
        },
        "required": ["name"],
    },
}


# --- Registry ---
registry.register(
    name="tool_describe",
    toolset="tool_management",
    schema=TOOL_DESCRIBE_SCHEMA,
    handler=lambda args, **kw: describe_tool(name=args.get("name", "")),
    emoji="📖",
)
