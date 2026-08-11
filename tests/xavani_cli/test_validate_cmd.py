# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for `xavani validate` (C06 + C13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xavani_cli import validate
from xavani_constants import get_xavani_home

pytestmark = pytest.mark.integration

GOOD_CONFIG = """\
model:
  default: anthropic/claude-sonnet-4
  provider: openrouter
agent:
  max_turns: 90
memory:
  memory_enabled: true
toolsets:
  - xavani-cli
"""


def _write_home(path: str, content: str) -> Path:
    target = get_xavani_home() / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


class TestValidateConfig:
    def test_all_checks_pass_returns_zero(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 0
        assert "All checks passed" in out

    def test_missing_config_returns_one(self, capsys):
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "config.yaml missing" in out

    def test_invalid_yaml_returns_one(self, capsys):
        _write_home("config.yaml", "model:\n  default: [unclosed\n")
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "not valid YAML" in out

    def test_schema_violation_returns_one(self, capsys):
        _write_home("config.yaml", "agent:\n  max_turns: ninety\n")
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "schema" in out.lower()
        assert "agent.max_turns" in out

    def test_schema_violation_toolsets_not_array(self, capsys):
        _write_home("config.yaml", "toolsets: xavani-cli\n")
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "toolsets" in out

    def test_good_schema_no_violations(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        validate.run_validate(None)
        out = capsys.readouterr().out
        assert "conforms to core JSON schema" in out


class TestValidateSecrets:
    def test_missing_env_returns_one(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert ".env missing" in out

    def test_no_provider_keys_returns_one(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "TERMINAL_ENV=local\nNOT_A_KEY=whatever\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "No provider API keys found" in out

    def test_whitespace_only_key_returns_one(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=   \n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "No provider API keys found" in out

    def test_blank_key_with_good_key_warns_but_passes(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=   \nANTHROPIC_API_KEY=sk-ant-ok\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 0
        assert "provider key(s) present but blank" in out


class TestValidateEnvironment:
    def test_unwritable_home_returns_one(self, monkeypatch, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        monkeypatch.setattr(validate, "_home_writable", lambda home: False)
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "XAVANI_HOME not writable" in out

    def test_writable_home_passes(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        assert code == 0


class TestValidateModelRegistry:
    def test_missing_default_model_returns_one(self, capsys):
        _write_home("config.yaml", "agent:\n  max_turns: 90\n")
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "No default model configured" in out

    def test_corrupt_model_catalog_cache_returns_one(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        catalog = get_xavani_home() / "cache" / "model_catalog.json"
        catalog.parent.mkdir(parents=True, exist_ok=True)
        catalog.write_text("{not json", encoding="utf-8")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 1
        assert "Model catalog cache is corrupt" in out

    def test_valid_model_catalog_cache_passes(self, capsys):
        _write_home("config.yaml", GOOD_CONFIG)
        _write_home(".env", "OPENAI_API_KEY=sk-test\n")
        catalog = get_xavani_home() / "cache" / "model_catalog.json"
        catalog.parent.mkdir(parents=True, exist_ok=True)
        catalog.write_text('{"models": []}', encoding="utf-8")
        code = validate.run_validate(None)
        out = capsys.readouterr().out
        assert code == 0
        assert "Model catalog cache is valid JSON" in out


class TestConfigSchema:
    def test_schema_accepts_core_sections(self):
        from xavani_cli.config_schema import validate_config_schema

        config = {
            "model": {"default": "x", "provider": "openrouter"},
            "agent": {"max_turns": 10, "gateway_timeout": 0},
            "memory": {"memory_enabled": True, "provider": ""},
            "toolsets": ["xavani-cli", "web"],
            "gateway": {"proxy_url": "http://localhost:9000"},
            "unknown_future_key": {"anything": 1},
        }
        assert validate_config_schema(config) == []

    def test_schema_rejects_wrong_types(self):
        from xavani_cli.config_schema import validate_config_schema

        errors = validate_config_schema(
            {
                "model": {"default": 42},
                "agent": {"max_turns": "many"},
                "toolsets": "xavani-cli",
                "gateway": "running",
            }
        )
        joined = "\n".join(errors)
        assert "model.default" in joined
        assert "agent.max_turns" in joined
        assert "toolsets" in joined
        assert "gateway" in joined

    def test_schema_rejects_non_mapping(self):
        from xavani_cli.config_schema import validate_config_schema

        errors = validate_config_schema(["not", "a", "mapping"])
        assert errors
        assert "mapping" in errors[0]
