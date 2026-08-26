# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for project scaffolders exposed by ``xavani new``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from xavani_cli.scaffold import (
    ScaffoldError,
    create_plugin,
    create_provider,
    create_skill,
    register_cli,
)


def test_skill_scaffold_uses_frontmatter_and_project_layout(tmp_path: Path) -> None:
    result = create_skill("incident-response", root=tmp_path, category="security")

    skill_md = tmp_path / "skills" / "security" / "incident-response" / "SKILL.md"
    assert result == skill_md
    assert skill_md.is_file()
    content = skill_md.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: incident-response" in content
    assert "categories:" in content
    assert "# Incident Response" in content


def test_plugin_scaffold_creates_manifest_and_registration(tmp_path: Path) -> None:
    result = create_plugin("calendar-tools", root=tmp_path)

    plugin_dir = tmp_path / "plugins" / "calendar-tools"
    assert result == plugin_dir
    assert (plugin_dir / "plugin.yaml").read_text(encoding="utf-8").count("api_version: 0.1.0") == 1
    init = (plugin_dir / "__init__.py").read_text(encoding="utf-8")
    assert "def register(ctx):" in init


def test_provider_scaffold_uses_model_provider_layout(tmp_path: Path) -> None:
    create_provider(
        "acme-ai",
        root=tmp_path,
        display_name="Acme AI",
        env_var="ACME_API_KEY",
        base_url="https://api.acme.example/v1",
        aliases=["acme"],
    )

    provider_dir = tmp_path / "plugins" / "model-providers" / "acme-ai"
    source = (provider_dir / "__init__.py").read_text(encoding="utf-8")
    manifest = (provider_dir / "plugin.yaml").read_text(encoding="utf-8")
    assert "${" not in source
    assert 'name="acme-ai"' in source
    assert 'display_name="Acme AI"' in source
    assert 'env_vars=("ACME_API_KEY",)' in source
    assert 'base_url="https://api.acme.example/v1"' in source
    assert 'aliases=("acme",)' in source
    assert "kind: model-provider" in manifest


def test_provider_scaffold_source_compiles(tmp_path: Path) -> None:
    provider_dir = create_provider("demo-provider", root=tmp_path, display_name="Demo Provider")
    source_path = provider_dir / "__init__.py"
    source = source_path.read_text(encoding="utf-8")

    assert source.splitlines()[0] == '"""Demo Provider provider profile."""'
    compile(source, str(source_path), "exec")


def test_scaffolders_refuse_existing_targets_without_force(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "existing" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("keep me", encoding="utf-8")

    with pytest.raises(ScaffoldError, match="already exists"):
        create_skill("existing", root=tmp_path)
    assert target.read_text(encoding="utf-8") == "keep me"


def test_force_is_explicit_and_replaces_target(tmp_path: Path) -> None:
    create_plugin("demo", root=tmp_path)
    target = tmp_path / "plugins" / "demo" / "plugin.yaml"
    target.write_text("custom: true\n", encoding="utf-8")

    create_plugin("demo", root=tmp_path, force=True)
    assert "custom: true" not in target.read_text(encoding="utf-8")
    assert "name: demo" in target.read_text(encoding="utf-8")


def test_names_are_filesystem_safe(tmp_path: Path) -> None:
    with pytest.raises(ScaffoldError, match="lowercase"):
        create_provider("../escape", root=tmp_path)


def test_new_parser_routes_all_scaffold_types() -> None:
    parser = argparse.ArgumentParser()
    register_cli(parser)

    skill = parser.parse_args(["skill", "my-skill"])
    plugin = parser.parse_args(["plugin", "my-plugin"])
    provider = parser.parse_args(["provider", "my-provider"])

    assert skill.new_type == "skill"
    assert plugin.new_type == "plugin"
    assert provider.new_type == "provider"
    assert skill.func is plugin.func is provider.func


def test_top_level_entry_routes_new_to_full_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    import xavani
    import xavani_cli.main as full_cli

    delegated = []
    monkeypatch.setattr(sys, "argv", ["xavani", "new", "skill", "demo"])
    monkeypatch.setattr(full_cli, "main", lambda: delegated.append(True))

    assert xavani._maybe_delegate_to_full_cli() is True
    assert delegated == [True]
