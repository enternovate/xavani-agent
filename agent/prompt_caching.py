# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Anthropic prompt caching strategy.

Two layouts, all cache_control breakpoints at the same TTL (5m or 1h):

- ``system_and_3`` (default, non-anthropic-messages paths): system prompt +
  last 3 non-system messages = 4 message-level breakpoints.
- ``tools_system_boundary`` (api_mode=anthropic_messages): tools block +
  system prompt + the last message of the stable history prefix (the
  oldest-kept boundary) = 3 breakpoints, leaving room inside Anthropic's
  hard limit of 4 cache_control breakpoints per request.

Byte-stability contract: the system prompt is built once per session and
replayed verbatim (see conversation_loop), and tool schemas are emitted in
deterministic sorted-by-name order (tools/registry.py) — both are required
for cross-turn cache hits. Reduces input token costs by ~70-75% on
multi-turn conversations within a single session.

Pure functions -- no class state, no AIAgent dependency.
"""

import copy
from typing import Any, Dict, List


def _apply_cache_marker(msg: dict, cache_marker: dict, native_anthropic: bool = False) -> None:
    """Add cache_control to a single message, handling all format variations."""
    role = msg.get("role", "")
    content = msg.get("content")

    if role == "tool":
        if native_anthropic:
            msg["cache_control"] = cache_marker
        return

    if content is None or content == "":
        msg["cache_control"] = cache_marker
        return

    if isinstance(content, str):
        msg["content"] = [
            {"type": "text", "text": content, "cache_control": cache_marker}
        ]
        return

    if isinstance(content, list) and content:
        last = content[-1]
        if isinstance(last, dict):
            last["cache_control"] = cache_marker


def _build_marker(ttl: str) -> Dict[str, str]:
    """Build a cache_control marker dict for the given TTL ('5m' or '1h')."""
    marker: Dict[str, str] = {"type": "ephemeral"}
    if ttl == "1h":
        marker["ttl"] = "1h"
    return marker


def apply_anthropic_cache_control(
    api_messages: List[Dict[str, Any]],
    cache_ttl: str = "5m",
    native_anthropic: bool = False,
    history_breakpoints: int = 3,
) -> List[Dict[str, Any]]:
    """Apply prompt-cache breakpoints to messages for Anthropic models.

    Places a cache_control breakpoint on the system prompt (breakpoint 2 in
    the request ordering: tools block → system → oldest-kept boundary) plus
    ``history_breakpoints`` trailing non-system messages. The oldest of those
    trailing markers is the "oldest-kept boundary" — the last message of the
    byte-stable history prefix, which is what makes cross-turn cache hits
    possible (new turns append at the end, so everything before the boundary
    is replayed verbatim).

    ``history_breakpoints`` defaults to 3 (legacy ``system_and_3`` strategy,
    4 message-level breakpoints). The api_mode=anthropic_messages path passes
    1 so the tools-block breakpoint (added by build_anthropic_kwargs) fits
    inside Anthropic's hard limit of 4 cache_control breakpoints per request.

    Returns:
        Deep copy of messages with cache_control breakpoints injected.
    """
    messages = copy.deepcopy(api_messages)
    if not messages:
        return messages

    marker = _build_marker(cache_ttl)

    breakpoints_used = 0

    if messages[0].get("role") == "system":
        _apply_cache_marker(messages[0], marker, native_anthropic=native_anthropic)
        breakpoints_used += 1

    remaining = min(history_breakpoints, 4 - breakpoints_used)
    non_sys = [i for i in range(len(messages)) if messages[i].get("role") != "system"]
    for idx in non_sys[-remaining:]:
        _apply_cache_marker(messages[idx], marker, native_anthropic=native_anthropic)

    return messages
