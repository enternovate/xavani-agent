# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Xavani Agent Deep Learning Layer — Phase 7.

The Xavani Learner system learns the user's personality, communication style,
humor, preferences, and favorite things to build, then uses that knowledge to
craft better responses. It consists of three subsystems:

- **UserProfile**: Deep user profiling that learns from every conversation.
  Stores personality traits, domain expertise, skill affinities, and
  communication preferences in ``~/.xavani/data/user_profile.json``.

- **ContextEnricher**: The reiteration layer between user and agent.
  Intercepts every user message, checks the user profile for relevant context,
  rewrites the message to include implicit context, scans for skill keywords,
  reiterates understanding back to the user, and forwards the enriched message.

- **SkillOrchestrator**: Intelligent skill matching from the 169 built-in
  skills. Scans user messages for keywords matching skill descriptions,
  ranks skills by relevance, loads skill context, and suggests skills the
  user hasn't tried but would benefit from.

All data is stored under ``~/.xavani/``. Zero telemetry, zero external
dependencies beyond the Python standard library.
"""

from __future__ import annotations

from .user_profile import UserProfile
from .context_enricher import ContextEnricher
from .skill_orchestrator import SkillOrchestrator

__all__ = [
    "UserProfile",
    "ContextEnricher",
    "SkillOrchestrator",
]
