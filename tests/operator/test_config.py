# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the product-config loader (v0.7.0 operator U2)."""

from __future__ import annotations

import pytest

from xavani_operator.config import ConfigError, ProductConfig, load_product_config


def _write(tmp_path, text: str):
    p = tmp_path / "xavani.product.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_minimal_config_loads_with_defaults(tmp_path):
    path = _write(tmp_path, "product:\n  name: Acme Widget\n")
    cfg = load_product_config(path)
    assert isinstance(cfg, ProductConfig)
    assert cfg.product.name == "Acme Widget"
    # Sensible defaults for omitted sections.
    assert cfg.goals == []
    assert cfg.channels == []
    assert cfg.budgets.max_actions_per_cycle == 10
    assert cfg.product.repo == "."


def test_full_config_parses_all_sections(tmp_path):
    path = _write(
        tmp_path,
        """
product:
  name: Acme Widget
  description: A widget that widgets
  repo: ./repo
  stack: [python, react]
goals:
  - id: g1
    intent: ship onboarding
    priority: 1
    success_metric: signups
channels:
  - platform: x
    handle: "@acme"
    cadence: daily
brand:
  voice: friendly
  dos: [be clear]
  donts: [no hype]
constraints:
  no_touch_paths: [secrets/]
  content_policy: no profanity
budgets:
  llm_tokens_per_day: 100000
  spend_per_day: 5.0
  max_actions_per_cycle: 3
approval:
  tier_overrides:
    post_external: 1
  auto_window: 600
schedule:
  cycle_cadence: "0 9 * * *"
  watchers: [repo, issues]
""",
    )
    cfg = load_product_config(path)
    assert cfg.product.stack == ["python", "react"]
    assert cfg.goals[0].id == "g1"
    assert cfg.goals[0].priority == 1
    assert cfg.channels[0].platform == "x"
    assert cfg.brand.voice == "friendly"
    assert cfg.constraints.no_touch_paths == ["secrets/"]
    assert cfg.budgets.max_actions_per_cycle == 3
    assert cfg.approval.tier_overrides["post_external"] == 1
    assert cfg.schedule.cycle_cadence == "0 9 * * *"
    assert cfg.schedule.watchers == ["repo", "issues"]


def test_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_product_config(tmp_path / "does_not_exist.yaml")


def test_missing_required_product_name_raises_configerror(tmp_path):
    path = _write(tmp_path, "product: {}\n")
    with pytest.raises(ConfigError):
        load_product_config(path)


def test_empty_file_raises_configerror(tmp_path):
    path = _write(tmp_path, "")
    with pytest.raises(ConfigError):
        load_product_config(path)


def test_blank_sections_fall_back_to_defaults(tmp_path):
    # A user comments out whole sections, leaving them empty (YAML null).
    path = _write(tmp_path, "product:\n  name: Acme\ngoals:\nchannels:\nbrand:\n")
    cfg = load_product_config(path)
    assert cfg.goals == []
    assert cfg.channels == []
    assert cfg.brand.voice == ""
