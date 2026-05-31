# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Computer-Use Tool — Drive screen/keyboard/mouse via MCP computer-use server.

Provides screenshot capture, keyboard input, mouse actions, and window
management through an MCP computer-use server. Guarded behind environment
checks so it only activates when the server is available.

Requires an MCP computer-use server configured in the agent's MCP settings.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------


def _check_computer_use_available() -> bool:
    """Check if computer-use MCP server is configured and available."""
    # Check for environment variable gate
    if os.environ.get("XAVANI_COMPUTER_USE", "").lower() not in ("1", "true", "yes"):
        return False

    # Check if MCP tool is available
    try:
        from tools.mcp_tool import get_mcp_tools
        tools = get_mcp_tools()
        # Look for computer-use related tools
        computer_tools = [t for t in tools if "computer" in t.get("name", "").lower()]
        return len(computer_tools) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def computer_screenshot(display: int = 0) -> str:
    """Capture a screenshot of the specified display."""
    try:
        from tools.mcp_tool import call_mcp_tool
        result = call_mcp_tool("computer_screenshot", {"display": display})
        return json.dumps({"ok": True, "screenshot": result})
    except Exception as exc:
        return json.dumps({"error": f"Screenshot failed: {exc}"})


def computer_click(x: int, y: int, button: str = "left") -> str:
    """Click at the specified coordinates."""
    try:
        from tools.mcp_tool import call_mcp_tool
        result = call_mcp_tool("computer_click", {"x": x, "y": y, "button": button})
        return json.dumps({"ok": True, "result": result})
    except Exception as exc:
        return json.dumps({"error": f"Click failed: {exc}"})


def computer_type(text: str) -> str:
    """Type the specified text via keyboard."""
    try:
        from tools.mcp_tool import call_mcp_tool
        result = call_mcp_tool("computer_type", {"text": text})
        return json.dumps({"ok": True, "result": result})
    except Exception as exc:
        return json.dumps({"error": f"Type failed: {exc}"})


def computer_key(key: str) -> str:
    """Press a special key (enter, tab, escape, etc.)."""
    try:
        from tools.mcp_tool import call_mcp_tool
        result = call_mcp_tool("computer_key", {"key": key})
        return json.dumps({"ok": True, "result": result})
    except Exception as exc:
        return json.dumps({"error": f"Key press failed: {exc}"})


def computer_scroll(direction: str, amount: int = 3) -> str:
    """Scroll in the specified direction (up, down, left, right)."""
    try:
        from tools.mcp_tool import call_mcp_tool
        result = call_mcp_tool("computer_scroll", {"direction": direction, "amount": amount})
        return json.dumps({"ok": True, "result": result})
    except Exception as exc:
        return json.dumps({"error": f"Scroll failed: {exc}"})


def computer_move(x: int, y: int) -> str:
    """Move the mouse cursor to the specified coordinates."""
    try:
        from tools.mcp_tool import call_mcp_tool
        result = call_mcp_tool("computer_move", {"x": x, "y": y})
        return json.dumps({"ok": True, "result": result})
    except Exception as exc:
        return json.dumps({"error": f"Move failed: {exc}"})


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------


def _handle_computer_use(args: Dict[str, Any]) -> str:
    """Tool handler for computer-use."""
    action = args.get("action", "")

    if action == "screenshot":
        return computer_screenshot(display=args.get("display", 0))
    elif action == "click":
        return computer_click(
            x=args.get("x", 0),
            y=args.get("y", 0),
            button=args.get("button", "left"),
        )
    elif action == "type":
        return computer_type(text=args.get("text", ""))
    elif action == "key":
        return computer_key(key=args.get("key", ""))
    elif action == "scroll":
        return computer_scroll(
            direction=args.get("direction", "down"),
            amount=args.get("amount", 3),
        )
    elif action == "move":
        return computer_move(x=args.get("x", 0), y=args.get("y", 0))
    else:
        return json.dumps({
            "error": f"Unknown action: {action}. "
                     "Use: screenshot, click, type, key, scroll, move."
        })


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

COMPUTER_USE_SCHEMA: Dict[str, Any] = {
    "name": "computer_use",
    "description": (
        "Drive the desktop via an MCP computer-use server. "
        "Actions: screenshot (capture screen), click (x,y + button), "
        "type (keyboard text), key (special keys), scroll (direction + amount), "
        "move (mouse cursor). Requires XAVANI_COMPUTER_USE=1 env var."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "click", "type", "key", "scroll", "move"],
                "description": "The computer-use action to perform.",
            },
            "x": {
                "type": "integer",
                "description": "X coordinate for click/move actions.",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate for click/move actions.",
            },
            "text": {
                "type": "string",
                "description": "Text to type.",
            },
            "key": {
                "type": "string",
                "description": "Special key to press (enter, tab, escape, backspace, delete, etc.).",
            },
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "description": "Mouse button for click action (default: left).",
            },
            "direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
                "description": "Scroll direction.",
            },
            "amount": {
                "type": "integer",
                "description": "Scroll amount (default: 3).",
            },
            "display": {
                "type": "integer",
                "description": "Display number for screenshot (default: 0).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

registry.register(
    name="computer_use",
    toolset="computer_use",
    schema=COMPUTER_USE_SCHEMA,
    handler=_handle_computer_use,
    check_fn=_check_computer_use_available,
    description="Drive screen/keyboard/mouse via MCP computer-use server.",
    emoji="🖥️",
)
