# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Downfall detector — wire the Oracle into the agent detector registry (v1.0.0 ②).

Exposes the Oracle's deterministic downfall check as a standard
:mod:`agent.detectors` detector, so the operator's autonomy safety gate, the CLI,
and CI can all run "does this plan rhyme with a known way the great fell?" with a
single token-free call (R10). The wisdom corpus is loaded lazily and cached, so
importing this module costs nothing until the detector actually runs.

Call :func:`register_downfall` once (e.g. when the operator starts) to add it to
the shared registry; or use :func:`downfall_detector` directly.
"""

from __future__ import annotations

from typing import Any

from agent.detectors import Verdict, register

_CORPUS = None


def _corpus():
    global _CORPUS
    if _CORPUS is None:
        from xavani_wisdom.patterns import load_corpus

        _CORPUS = load_corpus()
    return _CORPUS


def downfall_detector(context: dict[str, Any]) -> Verdict:
    """Flag a plan/decision that matches a known downfall signature. Deterministic."""
    from xavani_wisdom.consequence import detect_downfall

    text = str(context.get("text") or context.get("diff") or "")
    signals = detect_downfall({"text": text, "signals": context.get("signals", [])}, _corpus())
    return Verdict(
        detector="downfall",
        ok=not signals,
        findings=[f"downfall signal: {s}" for s in signals],
    )


def register_downfall() -> None:
    """Register the downfall detector in the shared agent registry (idempotent)."""
    register("downfall", downfall_detector)
