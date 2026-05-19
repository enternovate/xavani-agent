# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Browser Use cloud browser plugin — bundled, auto-loaded.

Mirrors the ``plugins/web/<vendor>/`` layout: ``provider.py`` holds the
provider class; ``__init__.py::register`` instantiates and registers it.
"""

from __future__ import annotations

from plugins.browser.browser_use.provider import BrowserUseBrowserProvider


def register(ctx) -> None:
    """Register the Browser Use provider with the plugin context."""
    ctx.register_browser_provider(BrowserUseBrowserProvider())
