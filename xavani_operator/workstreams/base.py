# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Workstream protocol + registry (v0.7.0 operator U20).

Defines the one interface every capability pack implements, and a tiny global
registry so the engine can discover packs by name. A pack contributes:

* ``detect_opportunities(perception, config)`` — deterministic (R10)
* ``make_plan(intent, ctx)``                    — the LLM generation surface
* ``execute(step, ctx)`` / ``verify(result, ctx)`` — dispatch + check

This module itself is pure and import-light (no LLM). Concrete packs (build /
promote / ops) register themselves in M4/M5.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Workstream(Protocol):
    """A pluggable capability pack on the operator engine."""

    name: str

    def detect_opportunities(self, perception: Any, config: Any) -> list: ...

    def make_plan(self, intent: Any, ctx: Any) -> Any: ...

    def execute(self, step: Any, ctx: Any) -> Any: ...

    def verify(self, result: Any, ctx: Any) -> Any: ...


_REGISTRY: dict[str, Workstream] = {}


def register_workstream(ws: Workstream) -> None:
    """Register a workstream pack under its ``name``."""
    _REGISTRY[ws.name] = ws


def get_workstream(name: str) -> Workstream | None:
    """Return the registered pack named ``name``, or ``None``."""
    return _REGISTRY.get(name)


def all_workstreams() -> dict[str, Workstream]:
    """A copy of the current name → pack registry."""
    return dict(_REGISTRY)


def clear_workstreams() -> None:
    """Empty the registry (used by tests for isolation)."""
    _REGISTRY.clear()
