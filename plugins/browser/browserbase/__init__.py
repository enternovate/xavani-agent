# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Browserbase cloud browser plugin — bundled, auto-loaded.

Mirrors the ``plugins/web/<vendor>/`` and ``plugins/image_gen/openai/``
layout: ``provider.py`` holds the provider class; ``__init__.py::register``
instantiates and registers it via the plugin context.
"""

from __future__ import annotations

from plugins.browser.browserbase.provider import BrowserbaseBrowserProvider


def register(ctx) -> None:
    """Register the Browserbase provider with the plugin context."""
    ctx.register_browser_provider(BrowserbaseBrowserProvider())
