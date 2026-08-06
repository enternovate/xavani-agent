# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic handler for the golden eval gate (harness item 1).

The gate runs every golden case's input through this handler and checks
that the expected substring appears. This file is the contract between
the eval cases and the steer behaviour under test: when steer semantics
change, update this handler and the cases together — that is the point
of the gate.
"""

from __future__ import annotations


def golden_handler(input_text: str) -> str:
    """Map golden eval inputs to canonical steer responses."""
    text = input_text.strip().lower()
    if text == "hello":
        return "hello back"
    if text.startswith("steer:"):
        return "steer acknowledged"
    return "unhandled"
