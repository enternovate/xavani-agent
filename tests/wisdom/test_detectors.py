# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the downfall detector wired into the agent registry (v1.0.0 ②)."""

from __future__ import annotations

from agent import detectors as reg
from xavani_wisdom.detectors import downfall_detector, register_downfall


def test_downfall_detector_passes_benign_plan() -> None:
    v = downfall_detector({"text": "write a unit test for the parser and ship it"})
    assert v.ok is True
    assert v.findings == []
    assert v.detector == "downfall"


def test_downfall_detector_flags_leverage_plan() -> None:
    v = downfall_detector(
        {"text": "borrow heavily, go all in, we cannot lose — scale fast and ignore the base rate"}
    )
    assert v.ok is False
    assert any("leverage" in f or "overextension" in f for f in v.findings)


def test_register_into_agent_registry() -> None:
    register_downfall()
    assert "downfall" in reg.names()
    v = reg.run("downfall", {"text": "hide the bad numbers and inflate the metrics at any cost"})
    assert v.ok is False
    assert any("fraud" in f or "metric_theatre" in f for f in v.findings)


def test_detector_is_deterministic() -> None:
    ctx = {"text": "protect the cash cow and ignore the disruption"}
    assert downfall_detector(ctx).findings == downfall_detector(ctx).findings
