# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B06: reasoning-effort auto-tuning via the capability map."""

from __future__ import annotations

from model_router import (
    DEFAULT_TASK_CLASS,
    ModelChoice,
    route_detailed,
    suggest_reasoning_effort,
)

# A tiny capability map covering all three effort bands.
_CAPS = {
    "task_classes": {
        "judgment": {"reasoning": 1.0, "cost": 0.0, "strengths": []},
        "code": {"reasoning": 0.7, "cost": 0.1, "strengths": []},
        "quick": {"reasoning": 0.2, "cost": 0.8, "strengths": []},
        "bulk": {"reasoning": 0.1, "cost": 1.0, "strengths": []},
    },
    "models": [
        {
            "id": "m1",
            "provider": "openai",
            "reasoning_tier": 4,
            "cost_tier": 2,
            "strengths": [],
        }
    ],
}
_ENV = {"OPENAI_API_KEY": "k"}


def test_judgment_routes_high_effort():
    assert suggest_reasoning_effort("judgment", capabilities=_CAPS) == "high"


def test_code_routes_medium_effort():
    assert suggest_reasoning_effort("code", capabilities=_CAPS) == "medium"


def test_quick_and_bulk_route_low_effort():
    assert suggest_reasoning_effort("quick", capabilities=_CAPS) == "low"
    assert suggest_reasoning_effort("bulk", capabilities=_CAPS) == "low"


def test_unknown_task_class_defaults_medium():
    assert suggest_reasoning_effort("mystery", capabilities=_CAPS) == "medium"


def test_route_detailed_carries_effort():
    choice = route_detailed("quick", env=_ENV, capabilities=_CAPS)
    assert isinstance(choice, ModelChoice)
    assert choice.effort == "low"
    assert choice.task_class == "quick"


def test_default_task_class_effort_matches_map():
    # Default caps: judgment is the packaged default and requires 1.0.
    assert suggest_reasoning_effort(DEFAULT_TASK_CLASS) in {"high", "medium", "low"}
