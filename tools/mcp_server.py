# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Expose Xavani's tool registry over the Model Context Protocol (v0.4.0 roadmap U32).

Turns this agent into an MCP *server*: any MCP-compatible client can list and
call Xavani's built-in tools. Tool schemas are reused verbatim from the local
tool registry, so the exposed surface always matches the agent's own tools.

Design for testability + safety:
  * ``exposed_tool_specs()`` — deterministic "what we expose" (name, description,
    inputSchema), excluding meta/agent-loop tools. No SDK needed; fully unit-tested.
  * ``_mcp_tool_objects`` / ``_text_result`` — the only places that touch the ``mcp``
    SDK types; thin and synchronous so tests exercise them directly.
  * ``build_server`` / ``serve_stdio`` — wire the deterministic surface to the SDK,
    dispatching calls through the same ``model_tools.handle_function_call`` the agent uses.
The ``mcp`` SDK is imported lazily, so importing this module never requires it.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Tools that must NOT be exposed to remote MCP clients (meta / agent-loop / unsafe).
_STATIC_DENYLIST = {"guidelines_gate", "delegate", "interrupt", "clarify"}


def exposed_tool_specs() -> List[Dict[str, Any]]:
    """Return ``[{name, description, inputSchema}]`` for tools to expose (deterministic)."""
    from tools.registry import discover_builtin_tools, registry

    discover_builtin_tools()  # populate the registry (idempotent)

    deny = set(_STATIC_DENYLIST)
    try:  # exclude tools the agent loop owns (they can't run via handle_function_call)
        from model_tools import _AGENT_LOOP_TOOLS  # type: ignore

        deny |= set(_AGENT_LOOP_TOOLS)
    except Exception:  # pragma: no cover - model_tools optional at this point
        pass

    specs: List[Dict[str, Any]] = []
    for name in sorted(registry.get_tool_to_toolset_map()):
        if name in deny:
            continue
        schema = registry.get_schema(name)
        if not schema:
            continue
        params = schema.get("parameters") or {"type": "object", "properties": {}}
        specs.append(
            {
                "name": name,
                "description": str(schema.get("description", name))[:1024],
                "inputSchema": params,
            }
        )
    return specs


def _mcp_tool_objects(specs: List[Dict[str, Any]]):
    """Build ``mcp.types.Tool`` objects from specs (isolated SDK usage; unit-tested)."""
    from mcp import types

    return [
        types.Tool(
            name=s["name"],
            description=s["description"],
            inputSchema=s["inputSchema"],
        )
        for s in specs
    ]


def _text_result(text: Any):
    """Wrap a string into MCP text content (isolated SDK usage; unit-tested)."""
    from mcp import types

    return [types.TextContent(type="text", text=str(text))]


def build_server(name: str = "xavani-agent"):
    """Construct a low-level MCP ``Server`` exposing the registry tools."""
    from mcp.server import Server

    specs = exposed_tool_specs()
    # Build Tool objects eagerly so any SDK/schema incompatibility surfaces now.
    tool_objects = _mcp_tool_objects(specs)
    exposed_names = {s["name"] for s in specs}

    server = Server(name)

    @server.list_tools()
    async def _list_tools():  # pragma: no cover - exercised via _mcp_tool_objects
        return tool_objects

    @server.call_tool()
    async def _call_tool(tool_name: str, arguments: Dict[str, Any] | None):  # pragma: no cover
        if tool_name not in exposed_names:
            return _text_result(f"unknown or non-exposed tool: {tool_name}")
        from model_tools import handle_function_call

        result = handle_function_call(tool_name, arguments or {}, task_id="mcp")
        return _text_result(result)

    return server


async def serve_stdio(name: str = "xavani-agent") -> None:  # pragma: no cover - runtime entry
    """Run the MCP server over stdio (for ``mcp``-client consumption)."""
    from mcp.server.stdio import stdio_server

    server = build_server(name)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


__all__ = ["exposed_tool_specs", "build_server", "serve_stdio"]
