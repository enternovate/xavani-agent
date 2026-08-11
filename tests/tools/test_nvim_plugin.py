# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F08: Neovim plugin tests."""

import json

from tools.nvim_plugin import generate_nvim_plugin, validate_plugin
import pytest

pytestmark = pytest.mark.unit


def test_generation_contains_required_files():
    files = generate_nvim_plugin("0.7.2")
    assert set(files.keys()) == {"lua/xavani/init.lua", "plugin/plugin.lua", "README.md", "version.json"}


def test_version_json():
    files = generate_nvim_plugin("0.7.2")
    assert json.loads(files["version.json"])["version"] == "0.7.2"


def test_lua_module_has_chat():
    files = generate_nvim_plugin("0.7.2")
    assert "function M.chat" in files["lua/xavani/init.lua"]
    assert "nvim_create_user_command" in files["lua/xavani/init.lua"]


def test_entry_point_sets_up_commands():
    files = generate_nvim_plugin("0.7.2")
    assert "setup_commands()" in files["plugin/plugin.lua"]


def test_validate_ok():
    assert validate_plugin(generate_nvim_plugin("0.7.2")) == []


def test_validate_empty():
    problems = validate_plugin({})
    assert any("missing" in p for p in problems)


def test_validate_bad_lua():
    files = generate_nvim_plugin("0.7.2")
    files["lua/xavani/init.lua"] = "return {}"
    problems = validate_plugin(files)
    assert any("M.chat" in p for p in problems)


def test_deterministic():
    assert generate_nvim_plugin("0.7.2") == generate_nvim_plugin("0.7.2")
