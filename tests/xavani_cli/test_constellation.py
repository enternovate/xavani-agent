# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the ``xavani constellation`` subcommand."""

from __future__ import annotations

from unittest.mock import patch

from xavani_cli import constellation
from xavani_cli.constellation import (
    CONSTELLATION_PACKAGES,
    _pip_install,
    _probe_version,
    _status_rows,
    build_constellation_parser,
    cmd_constellation,
)


def test_parser_registers_constellation() -> None:
    """The main() parser must expose the constellation subcommand."""
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.argv=['xavani', 'constellation', 'status'];"
            " from xavani_cli.main import main; raise SystemExit(main())",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Exit 1 (missing CLIs) proves the subcommand parsed and dispatched.
    assert proc.returncode in (0, 1)
    assert "Binary" in proc.stdout or "nyarhi" in proc.stdout


def test_status_prints_rows(capsys) -> None:
    """Status must print one row per constellation binary."""
    rows = [
        {"binary": "nyarhi", "installed": True, "version": "nyarhi 0.1.0"},
        {"binary": "gavaza", "installed": True, "version": "gavaza 0.1.0"},
        {"binary": "mhangani", "installed": True, "version": "mhangani 0.1.0"},
        {"binary": "constellation-mcp", "installed": True, "version": "0.1.0"},
    ]
    with patch.object(constellation, "_status_rows", return_value=rows):
        assert cmd_constellation(_args("status")) == 0
    out = capsys.readouterr().out
    assert "nyarhi" in out
    assert "constellation-mcp" in out
    assert "installed" in out


def test_status_flags_missing_binaries(capsys) -> None:
    """Missing binaries must be reported and yield exit code 1."""
    rows = [
        {"binary": "nyarhi", "installed": False, "version": "not found"},
        {"binary": "gavaza", "installed": True, "version": "gavaza 0.1.0"},
        {"binary": "mhangani", "installed": False, "version": "not found"},
        {"binary": "constellation-mcp", "installed": True, "version": "0.1.0"},
    ]
    with patch.object(constellation, "_status_rows", return_value=rows):
        assert cmd_constellation(_args("status")) == 1
    out = capsys.readouterr().out
    assert "missing" in out
    assert "nyarhi" in out


def test_probe_version_returns_none_for_missing() -> None:
    """A binary that is not on PATH must probe as missing."""
    with patch.object(constellation.shutil, "which", return_value=None):
        assert _probe_version("definitely-not-a-real-binary") is None


def test_probe_version_returns_output() -> None:
    """A binary on PATH must return its version line."""
    with patch.object(constellation.shutil, "which", return_value="/usr/bin/true"):
        version = _probe_version("true")
    assert version is not None
    assert "true" in version.lower() or version == "installed"


def test_install_prefers_uv() -> None:
    """Install must prefer uv when it is available."""
    with patch.object(constellation.shutil, "which", side_effect=lambda name: "/usr/bin/uv" if name == "uv" else None):
        with patch.object(constellation.subprocess, "run", return_value=_rc(0)) as run:
            assert _pip_install(upgrade=False) == 0
    argv = run.call_args.args[0]
    assert argv[0] == "/usr/bin/uv"
    assert argv[1:3] == ["pip", "install"]
    for package in CONSTELLATION_PACKAGES:
        assert package in argv


def test_install_falls_back_to_pip() -> None:
    """Install must fall back to the interpreter's pip without uv."""
    with patch.object(constellation.shutil, "which", return_value=None):
        with patch.object(constellation.subprocess, "run", return_value=_rc(0)) as run:
            assert _pip_install(upgrade=False) == 0
    argv = run.call_args.args[0]
    assert argv[0].endswith("python")
    assert argv[1:3] == ["-m", "pip"]


def test_update_uses_upgrade_flag() -> None:
    """Update must pass the upgrade flag to the installer."""
    with patch.object(constellation.shutil, "which", side_effect=lambda name: "/usr/bin/uv" if name == "uv" else None):
        with patch.object(constellation.subprocess, "run", return_value=_rc(0)) as run:
            assert _pip_install(upgrade=True) == 0
    argv = run.call_args.args[0]
    assert "--upgrade" in argv


def test_doctor_flags_missing_config(capsys, tmp_path, monkeypatch) -> None:
    """Doctor must warn when the MCP server is not configured."""
    monkeypatch.setenv("XAVANI_HOME", str(tmp_path))
    with patch.object(constellation, "_mcp_config_state", return_value={"configured": False, "command": ""}):
        with patch.object(constellation, "_status_rows", return_value=[]):
            assert cmd_constellation(_args("doctor")) == 1
    out = capsys.readouterr().out
    assert "not configured" in out


def test_doctor_ok_when_configured_and_installed(capsys) -> None:
    """Doctor must pass when the config and binaries are present."""
    with patch.object(constellation, "_mcp_config_state", return_value={"configured": True, "command": "constellation-mcp"}):
        with patch.object(constellation.shutil, "which", side_effect=lambda name: "/usr/bin/constellation-mcp" if name == "constellation-mcp" else "/usr/bin/nyarhi"):
            with patch.object(constellation, "_status_rows", return_value=[
                {"binary": "nyarhi", "installed": True, "version": "nyarhi 0.1.0"},
                {"binary": "gavaza", "installed": True, "version": "gavaza 0.1.0"},
                {"binary": "mhangani", "installed": True, "version": "mhangani 0.1.0"},
                {"binary": "constellation-mcp", "installed": True, "version": "0.1.0"},
            ]):
                assert cmd_constellation(_args("doctor")) == 0
    out = capsys.readouterr().out
    assert "All constellation checks passed" in out


def test_unknown_subcommand_raises() -> None:
    """An unknown subcommand must raise ValueError."""
    import pytest

    with pytest.raises(ValueError):
        cmd_constellation(_args("bogus"))


def _args(command: str):
    """Build a minimal argparse namespace."""
    from types import SimpleNamespace

    return SimpleNamespace(constellation_command=command)


def _rc(code: int):
    """Build a fake subprocess.CompletedProcess."""
    from types import SimpleNamespace

    return SimpleNamespace(returncode=code)


def test_build_constellation_parser_registers_four() -> None:
    """The constellation parser must expose four subcommands."""
    import argparse

    parser = argparse.ArgumentParser()
    build_constellation_parser(parser)
    for command in ("status", "install", "update", "doctor"):
        assert parser.parse_args([command]).constellation_command == command
