# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Capability layer — the agent's tools + skills, wired into the operator.

So the business operator isn't siloed: it can **discover** what the agent can do
(every registered tool, every installed skill) and **invoke** it. Workstreams,
the decision playbooks, and the propose step all consult :class:`Capabilities` to
pick the right tool/skill for a job (e.g. ``image_generation_tool`` +
``canvas-design`` for a poster; ``web_tools`` for research; Microsoft Graph for
email).

Discovery and matching are **deterministic** (R10) — listing tools/skills and
ranking them for a brief is pure Python. Only ``invoke_tool`` reaches the real
tool (the dispatch seam), so the layer is fully unit-tested with a fake registry.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _live_registry() -> Any:
    from tools.registry import registry

    # Tools register themselves on import; importing ``model_tools`` triggers all
    # the built-in ``registry.register`` calls. Do it once, lazily, when empty.
    if not registry.get_all_tool_names():
        try:
            import model_tools  # noqa: F401  (import for its registration side effects)
        except Exception:
            pass
    return registry


def list_skill_names(dirs: list[Path] | None = None) -> list[str]:
    """Discover installed skill names (folders containing a SKILL.md)."""
    if dirs is None:
        try:
            from agent.skill_utils import get_all_skills_dirs

            dirs = get_all_skills_dirs()
        except Exception:
            dirs = []
    names: set[str] = set()
    for d in dirs:
        try:
            for sub in Path(d).iterdir():
                if sub.is_dir() and (sub / "SKILL.md").exists():
                    names.add(sub.name)
        except OSError:
            continue
    return sorted(names)


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}


def _name_parts(name: str) -> set[str]:
    return {p for p in re.split(r"[^a-z0-9]+", name.lower()) if p}


class Capabilities:
    """The agent's tools + skills, discoverable and invokable by the operator."""

    def __init__(self, registry: Any = None, skill_names: list[str] | None = None) -> None:
        self._registry = registry
        self._skill_names = skill_names

    def _reg(self) -> Any:
        if self._registry is None:
            self._registry = _live_registry()
        return self._registry

    def tools(self) -> list[str]:
        try:
            return sorted(self._reg().get_all_tool_names())
        except Exception:
            return []

    def has_tool(self, name: str) -> bool:
        return name in self.tools()

    def invoke_tool(self, name: str, args: dict | None = None) -> str:
        """Dispatch a real tool (the only side-effecting method)."""
        return self._reg().dispatch(name, args or {})

    def skills(self) -> list[str]:
        if self._skill_names is not None:
            return sorted(self._skill_names)
        return list_skill_names()

    def find(self, brief: str, k: int = 8) -> dict[str, list[str]]:
        """Deterministically surface the tools/skills relevant to ``brief``."""
        toks = _tokens(brief)
        rel_tools = [t for t in self.tools() if _name_parts(t) & toks][:k]
        rel_skills = [s for s in self.skills() if _name_parts(s) & toks][:k]
        return {"tools": rel_tools, "skills": rel_skills}

    def as_context(self, brief: str | None = None) -> str:
        """A compact 'here's what I can use' block for generation/decision context."""
        if brief:
            rel = self.find(brief)
            tools, skills = rel["tools"], rel["skills"]
        else:
            tools, skills = self.tools()[:20], self.skills()[:20]
        return (
            "Available tools: " + (", ".join(tools) or "(none)") + "\n"
            "Available skills: " + (", ".join(skills) or "(none)")
        )
