# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F07: VS Code extension tests."""

import json

from tools.vscode_extension import (
    EXTENSION_NAME,
    generate_vscode_extension,
    validate_extension,
)


def test_generation_contains_required_files():
    files = generate_vscode_extension("0.7.2")
    assert set(files.keys()) == {"package.json", "src/extension.ts"}


def test_manifest_version_and_name():
    files = generate_vscode_extension("0.7.2")
    manifest = json.loads(files["package.json"])
    assert manifest["name"] == EXTENSION_NAME
    assert manifest["version"] == "0.7.2"


def test_manifest_contributes_commands():
    files = generate_vscode_extension("0.7.2")
    manifest = json.loads(files["package.json"])
    commands = manifest["contributes"]["commands"]
    assert any(c["command"] == "xavani.chat" for c in commands)
    assert any(c["command"] == "xavani.resume" for c in commands)


def test_manifest_configuration():
    files = generate_vscode_extension("0.7.2")
    manifest = json.loads(files["package.json"])
    properties = manifest["contributes"]["configuration"]["properties"]
    assert "xavani.baseUrl" in properties
    assert "xavani.apiKey" in properties


def test_extension_ts_activates_command():
    files = generate_vscode_extension("0.7.2")
    assert 'registerCommand("xavani.chat"' in files["src/extension.ts"]


def test_validate_ok():
    files = generate_vscode_extension("0.7.2")
    assert validate_extension(files) == []


def test_validate_missing_command():
    files = generate_vscode_extension("0.7.2")
    files["package.json"] = json.dumps({"name": "xavani-vscode", "contributes": {"commands": []}})
    problems = validate_extension(files)
    assert any("missing xavani.chat" in p for p in problems)


def test_validate_empty():
    problems = validate_extension({})
    assert problems
    assert any("missing" in p for p in problems)


def test_deterministic():
    assert generate_vscode_extension("0.7.2") == generate_vscode_extension("0.7.2")
