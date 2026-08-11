# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F06: xavani-core npm scaffold tests."""

import json

from tools.npm_scaffold import (
    PACKAGE_NAME,
    generate_npm_scaffold,
    validate_scaffold,
)
import pytest

pytestmark = pytest.mark.unit


def test_scaffold_contains_required_files():
    files = generate_npm_scaffold("0.7.2")
    assert set(files.keys()) == {"package.json", "src/index.ts", "README.md"}


def test_package_json_version_sync():
    files = generate_npm_scaffold("0.7.2")
    package = json.loads(files["package.json"])
    assert package["version"] == "0.7.2"
    assert package["name"] == PACKAGE_NAME


def test_typescript_client_contract():
    files = generate_npm_scaffold("0.7.2")
    assert "export class Xavani" in files["src/index.ts"]
    assert "async chat(message" in files["src/index.ts"]
    assert "baseUrl" in files["src/index.ts"]


def test_validate_scaffold_ok():
    files = generate_npm_scaffold("0.7.2")
    assert validate_scaffold(files) == []


def test_validate_missing_files():
    problems = validate_scaffold({})
    assert problems
    assert any("missing" in p for p in problems)


def test_validate_bad_version():
    files = generate_npm_scaffold("0.7.2")
    files["package.json"] = '{"name": "xavani-core"}'  # no version
    problems = validate_scaffold(files)
    assert any("version missing" in p for p in problems)


def test_deterministic_generation():
    a = generate_npm_scaffold("0.7.2")
    b = generate_npm_scaffold("0.7.2")
    assert a == b


def test_readme_documents_api():
    files = generate_npm_scaffold("0.7.2")
    assert "xavani.chat" in files["README.md"]
