# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from xavani_cli.config import (
    format_managed_message,
    get_managed_system,
    recommended_update_command,
)
from xavani_cli.main import cmd_update
from tools.skills_hub import OptionalSkillSource

pytestmark = pytest.mark.integration

# Managed-install detection and the skills-hub stub contract. The real
# OptionalSkillSource crawler was stripped from this fork; the managed-update
# logic below does not need it and runs in full.


def test_get_managed_system_homebrew(monkeypatch):
    monkeypatch.setenv("XAVANI_MANAGED", "homebrew")

    assert get_managed_system() == "Homebrew"
    assert recommended_update_command() == "brew upgrade xavani-agent"


def test_format_managed_message_homebrew(monkeypatch):
    monkeypatch.setenv("XAVANI_MANAGED", "homebrew")

    message = format_managed_message("update Xavani Agent")

    assert "managed by Homebrew" in message
    assert "brew upgrade xavani-agent" in message


def test_recommended_update_command_defaults_to_xavani_update(monkeypatch):
    monkeypatch.delenv("XAVANI_MANAGED", raising=False)

    # Also short-circuit the .managed marker path — CI runners may have an
    # ambient ~/.xavani/.managed if a prior test left XAVANI_HOME pointing
    # somewhere with that marker, which would make get_managed_update_command()
    # return "Update your Nix flake input ..." instead of falling through to
    # detect_install_method().
    with patch("xavani_cli.config.get_managed_update_command", return_value=None), \
         patch("xavani_cli.config.detect_install_method", return_value="git"):
        assert recommended_update_command() == "xavani update"


def test_cmd_update_blocks_managed_homebrew(monkeypatch, capsys):
    monkeypatch.setenv("XAVANI_MANAGED", "homebrew")

    with patch("xavani_cli.main.subprocess.run") as mock_run:
        cmd_update(SimpleNamespace())

    assert not mock_run.called
    captured = capsys.readouterr()
    assert "managed by Homebrew" in captured.err
    assert "brew upgrade xavani-agent" in captured.err


def test_optional_skill_source_stub_contract(monkeypatch, tmp_path):
    # The crawler is stripped in this fork — the stub must stay a safe
    # no-op: never raise, never return results, never touch the network.
    optional_dir = tmp_path / "optional-skills"
    optional_dir.mkdir()
    monkeypatch.setenv("XAVANI_OPTIONAL_SKILLS", str(optional_dir))

    source = OptionalSkillSource()

    assert source.name == "official"
    assert source.search("anything") == []
    assert source.inspect("any") is None
    assert source.fetch("any") is None
