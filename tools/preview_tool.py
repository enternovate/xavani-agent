#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
Preview dock control — lets the agent drive the desktop app preview pane.

The desktop backend injects XAVANI_DESKTOP_API (e.g. http://127.0.0.1:8642)
when the engine runs under the Electron host. This tool posts commands to
the backend's /desktop/api/preview/cmd route. Outside the desktop host the
tool reports clearly instead of failing, so CLI sessions stay unaffected.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional

VALID_ACTIONS = {"open", "close", "navigate", "status"}

_TIMEOUT_S = 5


def _desktop_api() -> Optional[str]:
    return os.environ.get("XAVANI_DESKTOP_API") or None


def _post(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except ValueError:
        return {"ok": False, "error": "Non-JSON response from desktop backend."}


def preview_control(
    action: str,
    url: str = "",
) -> Dict[str, Any]:
    """Send a preview-dock command to the desktop backend."""
    action = str(action).strip().lower()
    if action not in VALID_ACTIONS:
        return {
            "ok": False,
            "error": f"Unknown action '{action}'. Use one of: {sorted(VALID_ACTIONS)}.",
        }
    base = _desktop_api()
    if not base:
        return {
            "ok": False,
            "error": (
                "Preview control is only available inside the Xavani "
                "desktop app. Run the agent from the desktop app and retry."
            ),
        }
    if action in ("open", "navigate") and not str(url).strip():
        return {"ok": False, "error": f"Action '{action}' needs a url."}

    try:
        return _post(f"{base}/desktop/api/preview/cmd",
                     {"action": action, "url": str(url).strip()})
    except OSError as exc:
        return {"ok": False, "error": f"Desktop backend unreachable: {exc}"}


PREVIEW_CONTROL_SCHEMA = {
    "name": "preview_control",
    "description": (
        "Drive the desktop app's preview pane: open/navigate a URL, close "
        "the dock, or read its status. Desktop-app sessions only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "One of: open, navigate, close, status.",
            },
            "url": {
                "type": "string",
                "description": "Target URL for open/navigate.",
            },
        },
        "required": ["action"],
    },
}


def _handle_preview_control(args: Dict[str, Any]) -> str:
    return json.dumps(preview_control(**args), indent=2)


from tools.registry import registry  # noqa: E402

registry.register(
    name="preview_control",
    toolset="files",
    schema=PREVIEW_CONTROL_SCHEMA,
    handler=_handle_preview_control,
    description="Control the desktop preview pane.",
    emoji="🖥",
)
