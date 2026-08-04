# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C12: plugin API versioning gate.

Plugins declare the Xavani plugin API version they were built against
(``api_version`` in their manifest). The gate rejects plugins that
declare a version the current runtime does not support — a plugin built
for an older API can silently break on new hosts, and a plugin claiming
a future API is untrustworthy.

Version policy: the runtime supports exactly ``PLUGIN_API_VERSION`` and
nothing else. Plugin API changes are breaking by design until 1.0;
increments happen with the core release.

Usage::

    from tools.plugin_api_gate import (
        PLUGIN_API_VERSION,
        check_plugin_api_version,
    )

    verdict = check_plugin_api_version(manifest)
    if not verdict["compatible"]:
        raise PluginLoadError(verdict["reason"])
"""

from __future__ import annotations

import re
from typing import Any, Dict

PLUGIN_API_VERSION = "0.1.0"

# Manifest keys that may carry the version (common plugin conventions).
_MANIFEST_KEYS = ("api_version", "apiVersion", "xavani_api_version")

_VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def _extract_declared_version(manifest: Dict[str, Any]) -> str | None:
    if not isinstance(manifest, dict):
        return None
    for key in _MANIFEST_KEYS:
        value = manifest.get(key)
        if value is not None:
            return str(value)
    return None


def check_plugin_api_version(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Check a plugin manifest against the current API version.

    Returns a dict with ``compatible`` (bool) and ``reason`` (str).
    A plugin with NO declared version is REJECTED — an undeclared API
    contract cannot be trusted.
    """
    declared = _extract_declared_version(manifest)
    if declared is None:
        return {
            "compatible": False,
            "reason": (
                f"plugin declares no api_version; current API is "
                f"{PLUGIN_API_VERSION} (set api_version in the manifest)"
            ),
        }
    if not _VERSION_RE.match(declared):
        return {
            "compatible": False,
            "reason": f"plugin api_version '{declared}' is not a valid version",
        }
    if declared != PLUGIN_API_VERSION:
        return {
            "compatible": False,
            "reason": (
                f"plugin api_version {declared} does not match runtime "
                f"{PLUGIN_API_VERSION}"
            ),
        }
    return {"compatible": True, "reason": ""}


def gate_plugin_load(manifest: Dict[str, Any]) -> None:
    """Raise ValueError when the plugin manifest is incompatible."""
    verdict = check_plugin_api_version(manifest)
    if not verdict["compatible"]:
        raise ValueError(verdict["reason"])
