# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Exa web search + extract plugin — bundled, auto-loaded.

Backed by the official Exa SDK (``exa-py``). Both search and extract are
sync; the dispatcher in :mod:`tools.web_tools` handles the wrap when the
caller is async.
"""

from __future__ import annotations

from plugins.web.exa.provider import ExaWebSearchProvider


def register(ctx) -> None:
    """Register the Exa provider with the plugin context."""
    ctx.register_web_search_provider(ExaWebSearchProvider())
