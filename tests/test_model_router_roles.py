# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for model_router role resolution."""

import pytest

from model_router import MODEL_ROLES, resolve_role, resolve_role_model

CAPS = {
    "task_classes": {
        "judgment": {"reasoning": 1.0, "cost": 0.0, "strengths": ["judgment"]},
        "bulk": {"reasoning": 0.1, "cost": 1.0, "strengths": ["fast", "bulk"]},
        "code": {"reasoning": 0.7, "cost": 0.1, "strengths": ["code"]},
        "long_context": {"reasoning": 0.5, "cost": 0.1, "strengths": ["long_context"]},
    },
    "models": [
        {"id": "big-model", "provider": "prov-a", "reasoning_tier": 5,
         "cost_tier": 4, "strengths": ["judgment", "reasoning", "writing", "long_context", "code"]},
        {"id": "cheap-model", "provider": "prov-b", "reasoning_tier": 1,
         "cost_tier": 1, "strengths": ["fast", "bulk"]},
    ],
}

ENV = {"PROV_A_API_KEY": "k", "PROV_B_API_KEY": "k"}


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(
        "model_router._PROVIDER_ENV",
        {"prov-a": ["PROV_A_API_KEY"], "prov-b": ["PROV_B_API_KEY"]},
    )


def test_roles_are_the_documented_five():
    assert MODEL_ROLES == ("default", "smol", "slow", "plan", "advisor")


def test_unknown_role_raises():
    with pytest.raises(ValueError):
        resolve_role("bogus", capabilities=CAPS)


def test_smol_resolves_to_bulk_class(providers):
    choice = resolve_role("smol", env=ENV, capabilities=CAPS)
    assert choice is not None
    assert choice.model == "cheap-model"
    assert choice.task_class == "bulk"


def test_default_resolves_to_judgment_class(providers):
    choice = resolve_role("default", env=ENV, capabilities=CAPS)
    assert choice is not None
    assert choice.model == "big-model"
    assert choice.task_class == "judgment"


def test_explicit_override_wins_over_task_class(providers):
    cfg = {"smol": "prov-a/big-model"}
    choice = resolve_role("smol", env=ENV, capabilities=CAPS, role_config=cfg)
    assert choice is not None
    assert choice.model == "big-model"
    assert choice.provider == "prov-a"
    assert choice.reason.startswith("explicit model_roles.smol")


def test_resolve_role_model_returns_id_or_none(providers):
    assert resolve_role_model("slow", env=ENV, capabilities=CAPS) == "big-model"
    empty_env = {}
    assert resolve_role_model("slow", env=empty_env, capabilities=CAPS) is None
