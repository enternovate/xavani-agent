# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Memory Layer — Phase 4.

Episodic and procedural memory system for the Xavani Agent.

The memory layer provides:
- **EpisodicMemory**: SQLite-backed storage of agent-user episodes with
  full-text search, time-range queries, cross-agent context sharing, and
  conflict resolution.
- **ProceduralMemory**: Learns from repeated patterns by recording task
  outcomes, identifying optimal approaches, and building confidence scores.
- **MemoryManager**: Orchestrates both memory types into a unified system
  that remembers everything (user input → thought → action → result → outcome)
  and provides recall context to the agent prompt automatically.

All data is stored under ``~/.xavani/data/``. Zero telemetry, zero external
dependencies beyond the Python standard library.
"""

from __future__ import annotations

from .episodic import EpisodicMemory
from .procedural import ProceduralMemory
from .manager import MemoryManager

__all__ = [
    "EpisodicMemory",
    "ProceduralMemory",
    "MemoryManager",
]
