# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic per-turn tool pre-filter (v0.4.0 roadmap U8).

Selects the subset of tools relevant to a user message using pure-Python
keyword/intent rules — **no LLM call** (R10) — so the function-call schema sent
to the model shrinks and input-token cost drops on every turn.

Safety contract (never hide a needed tool):
  * When the message shows **no** clear intent, return the **full** tool set.
  * A small set of essentials (file ops, terminal, memory, messaging, skills) is
    **always** included, regardless of intent.
  * Output preserves the caller's input order, so the result is deterministic.

This module is intentionally side-effect-free and import-light; wiring it into
the schema build (``model_tools.get_definitions``) is opt-in via the caller.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence

# Essentials that must always be offered to the model, whatever the intent.
_ALWAYS_SUBSTRINGS: tuple[str, ...] = (
    "file", "terminal", "todo", "clarify", "send_message", "memory",
    "skill", "delegate",
)

# Intent regex -> tool-name substrings that serve that intent.
_INTENT_RULES: Dict[str, tuple[str, ...]] = {
    r"\b(browse|browser|web ?page|website|url|https?|navigate|scrape|crawl|dom)\b":
        ("browser", "web_tools", "url"),
    r"\b(search|google|look ?up|find online|exa|firecrawl|parallel)\b":
        ("web_tools", "x_search", "search"),
    r"\b(tweet|twitter|\bx\.com\b)\b": ("x_search", "x_"),
    r"\b(image|picture|photo|screenshot|diagram|render|draw|logo|art)\b":
        ("image", "vision", "video"),
    r"\b(video|animation|animate|clip|movie)\b": ("video", "manim"),
    r"\b(voice|speak|say|audio|tts|transcribe|speech|listen)\b":
        ("tts", "transcription", "voice", "neutts"),
    r"\b(remember|memory|recall|earlier|previously|history|last time)\b":
        ("memory", "session_search"),
    r"\b(schedule|cron|every day|recurring|reminder|periodic)\b": ("cron",),
    r"\b(discord|telegram|slack|whatsapp|signal|matrix|dm|notify)\b":
        ("send_message", "discord"),
    r"\b(run|execute|python|bash|shell|compile|script|code)\b":
        ("code_execution", "terminal"),
    r"\b(mcp|model context protocol)\b": ("mcp",),
    r"\b(ensemble|mixture of agents|multiple models|subagent|sub-agent|parallel agents)\b":
        ("delegate", "mixture_of_agents"),
    r"\b(eval|evaluate|benchmark|test ?suite|pass ?rate)\b": ("eval_harness",),
    r"\b(home ?assistant|smart ?home|thermostat|light bulb|hvac)\b": ("homeassistant",),
    r"\b(computer ?use|control the screen|click|keyboard|mouse|gui)\b": ("computer_use",),
    r"\b(kanban|board|task list|backlog)\b": ("kanban", "todo"),
}


def _matches_any(tool: str, substrings: Iterable[str]) -> bool:
    return any(s in tool for s in substrings)


def select_tools(text: str, all_tools: Sequence[str]) -> List[str]:
    """Return the relevant subset of ``all_tools`` for ``text`` (deterministic).

    Falls back to the full list when intent is unclear so no needed tool is
    ever hidden. Essentials are always included.
    """
    tools = list(all_tools)
    if not text or not text.strip():
        return tools

    low = text.lower()
    matched_intent = False
    wanted: set[str] = set()

    for pattern, subs in _INTENT_RULES.items():
        if re.search(pattern, low):
            matched_intent = True
            for t in tools:
                if _matches_any(t, subs):
                    wanted.add(t)

    # No recognizable intent -> don't risk hiding a tool; offer everything.
    if not matched_intent:
        return tools

    # Always include essentials.
    for t in tools:
        if _matches_any(t, _ALWAYS_SUBSTRINGS):
            wanted.add(t)

    # If filtering didn't meaningfully reduce the set, just return the full list.
    filtered = [t for t in tools if t in wanted]
    if not filtered or len(filtered) >= len(tools):
        return tools
    return filtered


def filter_definitions(
    text: str,
    definitions: Sequence[dict],
    *,
    name_key: str = "name",
) -> List[dict]:
    """Filter a list of tool *schema dicts* by relevance to ``text``.

    Looks up each definition's name via ``name_key`` (supporting the common
    OpenAI-style ``{"function": {"name": ...}}`` nesting) and keeps only the
    selected subset, preserving order. Unknown-shaped entries are kept.
    """
    def _name(d: dict) -> str:
        if name_key in d:
            return str(d[name_key])
        fn = d.get("function")
        if isinstance(fn, dict) and "name" in fn:
            return str(fn["name"])
        return ""

    names = [_name(d) for d in definitions]
    keep = set(select_tools(text, [n for n in names if n]))
    result: List[dict] = []
    for d, n in zip(definitions, names):
        if not n or n in keep:
            result.append(d)
    return result


__all__ = ["select_tools", "filter_definitions"]
