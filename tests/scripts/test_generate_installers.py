# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F03: native installer generator tests."""

import subprocess
import sys

import pytest

import scripts.generate_installers as gi


def test_generate_returns_both_scripts():
    generated = gi.generate_installers("0.7.2")
    assert set(generated.keys()) == {"install.sh", "install.ps1"}


def test_bash_script_contains_version():
    content = gi.generate_installers("0.7.2")["install.sh"]
    assert "0.7.2" in content
    assert "XAVANI_HOME" in content
    assert "tar -xzf" in content


def test_ps1_script_contains_version():
    content = gi.generate_installers("0.7.2")["install.ps1"]
    assert "0.7.2" in content
    assert "Expand-Archive" in content


def test_deterministic_output():
    a = gi.generate_installers("0.7.2")
    b = gi.generate_installers("0.7.2")
    assert a == b


def test_version_changes_output():
    a = gi.generate_installers("0.7.2")
    b = gi.generate_installers("0.8.0")
    assert a != b


def test_custom_base_url():
    content = gi.generate_installers(
        "0.7.2", base_url="https://example.com/releases"
    )["install.sh"]
    # Full-string assertion — substring checks on URLs are an
    # incomplete-sanitization pattern (CodeQL 1276).
    assert "https://example.com/releases" in content


def test_goldens_match_generated():
    """The committed goldens must match generated output exactly."""
    assert gi.check_goldens("0.7.2") is True


def test_check_script_runs():
    result = subprocess.run(
        [sys.executable, "scripts/generate_installers.py", "--version", "0.7.2", "--check"],
        capture_output=True, text=True, timeout=60,
        cwd=gi.REPO_ROOT,
    )
    assert result.returncode == 0
    assert "DRIFT" not in result.stdout + result.stderr


def test_generate_script_writes_files(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/generate_installers.py", "--version", "0.9.9", "--out", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
        cwd=gi.REPO_ROOT,
    )
    assert result.returncode == 0
    assert (tmp_path / "install.sh").exists()
    assert (tmp_path / "install.ps1").exists()
