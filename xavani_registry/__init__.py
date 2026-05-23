# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Agent Package Manager / Registry — Phase 2.

Manages the installation, removal, update, and discovery of MCP servers
from a built-in registry with package signing verification and security scanning.
"""

from __future__ import annotations

from .manager import OAGRegistry

__all__ = ["OAGRegistry"]
