#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""tool_call — invoke any registered tool by name.

Deferred tools are not wired into the default per-turn schema list, but they
remain fully registered and dispatchable. This meta-tool routes the call
through ``model_tools.handle_function_call`` — the same path the agent loop
uses — so plugin hooks (pre_tool_call / post_tool_call / transform_tool_result),
approvals, and ACP edit guards all run for the inner tool exactly as they
would for a directly-listed tool.
"""

from tools.registry import registry, tool_error


def invoke_tool_by_name(args: dict, **kwargs) -> str:
    """Dispatch *name* with *arguments* through the registry dispatch path."""
    name = args.get("name", "")
    arguments = args.get("arguments")

    if not name or not isinstance(name, str):
        return tool_error("name is required")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return tool_error("arguments must be an object")

    # Guard against unbounded self-recursion.
    if name == "tool_call":
        return tool_error("tool_call cannot invoke itself; call the target tool directly")

    # model_tools is already imported (it dispatches us); the import here is
    # a cheap sys.modules hit. handle_function_call runs hooks + approvals
    # and returns the inner tool's JSON string result, or an error JSON
    # string for unknown tools — it never raises for unknown names.
    from model_tools import handle_function_call

    try:
        return handle_function_call(
            name,
            arguments,
            task_id=kwargs.get("task_id"),
            user_task=kwargs.get("user_task"),
        )
    except Exception as exc:  # defensive: never raise from a tool handler
        return tool_error(f"Failed to dispatch {name}: {type(exc).__name__}: {exc}")


# =============================================================================
# OpenAI Function-Calling Schema
# =============================================================================

TOOL_CALL_SCHEMA = {
    "name": "tool_call",
    "description": (
        "Invoke a tool by name with the given arguments. Use this to call "
        "tools that are not listed on the default wire (discover them with "
        "tool_search / tool_describe first). Argument shape must match the "
        "target tool's schema. Policy, hooks, and approvals run exactly as "
        "for any directly-listed tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Exact tool name to invoke.",
            },
            "arguments": {
                "type": "object",
                "description": "Arguments for the tool, matching its schema.",
                "additionalProperties": True,
            },
        },
        "required": ["name"],
    },
}


# --- Registry ---
registry.register(
    name="tool_call",
    toolset="tool_management",
    schema=TOOL_CALL_SCHEMA,
    handler=invoke_tool_by_name,
    emoji="🚀",
)
