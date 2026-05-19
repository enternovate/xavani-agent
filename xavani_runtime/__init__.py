# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Agent Runtime — Phase 6.

Portable Agent Image format, loader, and lifecycle runner for the Xavani Agent.
Supports defining agents declaratively with .agent.toml files, loading them
from the local filesystem or registry, and managing their full lifecycle.

All data is stored under ``~/.xavani/``. Zero telemetry.
"""

from __future__ import annotations

from .image import AgentImage
from .loader import ImageLoader
from .runner import AgentRunner

__all__ = [
    "AgentImage",
    "ImageLoader",
    "AgentRunner",
]
