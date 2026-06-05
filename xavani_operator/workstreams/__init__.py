# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Operator workstream packs (v0.7.0 operator U20+).

A *workstream* is a pluggable capability pack on the one operator engine. Each
pack implements the :class:`~xavani_operator.workstreams.base.Workstream`
protocol and contributes opportunity rules, plan generation, execution, and
verification for its domain:

* ``build``   — software lifecycle (M4)
* ``promote`` — growth & marketing (M5)
* ``ops``     — operations / housekeeping

This module exposes the protocol and registry; the concrete packs land in their
own milestones.
"""

from __future__ import annotations

from xavani_operator.workstreams.base import (
    Workstream,
    all_workstreams,
    clear_workstreams,
    get_workstream,
    register_workstream,
)

__all__ = [
    "Workstream",
    "all_workstreams",
    "clear_workstreams",
    "get_workstream",
    "register_workstream",
]
