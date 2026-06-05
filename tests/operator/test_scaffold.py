# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for `xavani operator init` scaffolding (v0.7.0 operator U5)."""

from __future__ import annotations

import pytest

from xavani_operator.config import load_product_config
from xavani_operator.scaffold import CONFIG_FILENAME, init_product_config, starter_product_yaml


def test_starter_yaml_is_a_valid_config(tmp_path):
    text = starter_product_yaml("Acme Widget")
    path = tmp_path / CONFIG_FILENAME
    path.write_text(text, encoding="utf-8")
    cfg = load_product_config(path)
    assert cfg.product.name == "Acme Widget"


def test_init_writes_a_loadable_config(tmp_path):
    path = init_product_config(tmp_path, name="Acme Widget")
    assert path.name == CONFIG_FILENAME
    assert path.exists()
    assert load_product_config(path).product.name == "Acme Widget"


def test_init_refuses_to_overwrite_without_force(tmp_path):
    init_product_config(tmp_path, name="Acme")
    with pytest.raises(FileExistsError):
        init_product_config(tmp_path, name="Acme")


def test_init_force_overwrites(tmp_path):
    init_product_config(tmp_path, name="Acme")
    path = init_product_config(tmp_path, name="Beta", force=True)
    assert load_product_config(path).product.name == "Beta"


def test_init_has_a_nonempty_default_name(tmp_path):
    path = init_product_config(tmp_path)
    assert load_product_config(path).product.name


def test_starter_yaml_quotes_are_safe(tmp_path):
    # A name with a stray double-quote must not produce invalid YAML.
    text = starter_product_yaml('My "Great" Product')
    path = tmp_path / CONFIG_FILENAME
    path.write_text(text, encoding="utf-8")
    cfg = load_product_config(path)  # must not raise
    assert cfg.product.name
