# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the debug-friendly state dump (E05).

``tools/state_dump.py`` serializes ``~/.xavani`` config/session state to a
redacted JSON string: API keys and tokens must never survive into the dump.
"""

import json

import pytest

from tools.state_dump import redact, state_dump

pytestmark = pytest.mark.integration


def _write_config(home, content: str):
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(content, encoding="utf-8")


def test_state_dump_returns_valid_json_for_empty_home(tmp_path):
    missing_home = tmp_path / "does-not-exist"
    dump = state_dump(xavani_home=str(missing_home))
    payload = json.loads(dump)
    assert payload["xavani_home"] == str(missing_home)
    assert payload["exists"] is False
    assert payload["config"] == {}
    assert payload["session_files"] == []
    assert "environment" in payload


def test_state_dump_redacts_api_keys_and_tokens(tmp_path):
    _write_config(
        tmp_path,
        "model:\n"
        "  provider: openai\n"
        "  api_key: sk-0123456789abcdef\n"
        "web:\n"
        "  auth_token: wb-abcdef1234567890\n"
        "display:\n"
        "  compact: true\n",
    )
    dump = state_dump(xavani_home=str(tmp_path))
    payload = json.loads(dump)
    config = payload["config"]
    assert config["display"]["compact"] is True
    # Secret-shaped keys are masked, not leaked.
    assert config["model"]["api_key"] != "sk-0123456789abcdef"
    assert "sk-0123456789abcdef" not in dump
    assert "wb-abcdef1234567890" not in dump
    assert "***" in config["model"]["api_key"]


def test_state_dump_redacts_nested_secrets(tmp_path):
    _write_config(
        tmp_path,
        "providers:\n"
        "  - name: anthropic\n"
        "    api_key: sk-ant-0123456789\n"
        "  - name: groq\n"
        "    api_key: gsk-abcdefghijklmnop\n",
    )
    dump = state_dump(xavani_home=str(tmp_path))
    assert "sk-ant-0123456789" not in dump
    assert "gsk-abcdefghijklmnop" not in dump
    payload = json.loads(dump)
    providers = payload["config"]["providers"]
    assert len(providers) == 2
    assert all("***" in p["api_key"] for p in providers)


def test_state_dump_handles_corrupt_config(tmp_path):
    (tmp_path / "config.yaml").write_text("{{{ not yaml", encoding="utf-8")
    dump = state_dump(xavani_home=str(tmp_path))
    payload = json.loads(dump)
    assert "_error" in payload["config"]


def test_state_dump_includes_recent_session_files(tmp_path):
    (tmp_path / "sessions").mkdir(parents=True)
    (tmp_path / "sessions" / "a.json").write_text(
        json.dumps({"session_id": "abc", "api_key": "sk-12345678901234567890"}),
        encoding="utf-8",
    )
    dump = state_dump(xavani_home=str(tmp_path))
    assert "sk-12345678901234567890" not in dump
    payload = json.loads(dump)
    assert payload["session_files"][0]["file"] == "a.json"


def test_redact_masks_long_opaque_strings_even_with_generic_key():
    blob = "x" * 40
    assert redact({"encrypted": blob}) == {"encrypted": "xxxx...***"}
    # Short values under a generic key survive untouched.
    assert redact({"encrypted": "short"}) == {"encrypted": "short"}


def test_redact_preserves_plain_structure():
    value = {"a": {"b": [1, 2, {"c": "plain"}]}, "d": None}
    assert redact(value) == value


def test_state_dump_registered_in_registry():
    """The tool must be registered so get_definitions can surface it."""
    import tools.state_dump  # noqa: F401 — import triggers registration

    from tools.registry import registry

    definitions = registry.get_definitions({"state_dump"})
    assert any(
        d["function"]["name"] == "state_dump" for d in definitions
    )
