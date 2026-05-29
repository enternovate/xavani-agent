# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Realtime speech subpackage for the google_meet plugin (v2).

Provides a thin OpenAI Realtime API client and a file-queue speaker
wrapper so the Meet bot can play synthesized speech through the
virtual audio bridge.
"""

from .openai_client import RealtimeSession, RealtimeSpeaker  # noqa: F401

__all__ = ["RealtimeSession", "RealtimeSpeaker"]
