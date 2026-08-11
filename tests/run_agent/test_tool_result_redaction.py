# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D01: secret redaction on tool output (config-gated).

Tool results are masked before they enter the model context: API-key
shaped strings (sk-..., ghp_..., ENV assignments, JSON key fields) are
redacted in plain string results and in multimodal content-part text.
The env gate (XAVANI_REDACT_SECRETS) controls it; default is on.
"""

from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent

pytestmark = pytest.mark.unit


@pytest.fixture()
def agent():
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        a = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        a.client = MagicMock()
        return a


def test_string_result_masks_api_key(agent):
    out = agent._tool_result_content_for_active_model(
        "read_file", "config: OPENAI_API_KEY=sk-abc123def456"
    )
    assert "sk-abc123def456" not in out
    assert "OPENAI_API_KEY=" in out  # the key name stays visible


def test_string_result_masks_ghp_token(agent):
    out = agent._tool_result_content_for_active_model(
        "terminal", "token ghp_1234567890abcdef"
    )
    assert "ghp_1234567890abcdef" not in out


def test_plain_text_passes_through(agent):
    out = agent._tool_result_content_for_active_model(
        "read_file", "just normal file content"
    )
    assert out == "just normal file content"


def test_json_field_masked(agent):
    out = agent._tool_result_content_for_active_model(
        "read_file", '{"apiKey": "sk-live-98765"}'
    )
    assert "sk-live-98765" not in out


def test_multimodal_text_part_masked(agent):
    result = {
        "_multimodal": True,
        "content": [
            {"type": "text", "text": "OPENAI_API_KEY=sk-zzz111222"},
            {"type": "image_url", "image_url": {"url": "data:..."}},
        ],
    }
    out = agent._tool_result_content_for_active_model("browser", result)
    # The fixture model is not vision-capable, so the fallback is a summary
    # string; a vision-capable model would get the redacted content list.
    if isinstance(out, list):
        text_part = [p for p in out if isinstance(p, dict) and p.get("type") == "text"][0]
        assert "sk-zzz111222" not in text_part["text"]
        assert any(p.get("type") == "image_url" for p in out)
    else:
        assert "sk-zzz111222" not in str(out)


def test_opt_out_env_passes_secrets_through(agent, monkeypatch):
    monkeypatch.setenv("XAVANI_REDACT_SECRETS", "false")
    # redact_sensitive_text reads the env at import; force re-read via the
    # module-level flag check by calling with force=False.
    import agent.redact as _redact

    monkeypatch.setattr(_redact, "_REDACT_ENABLED", False)
    out = agent._tool_result_content_for_active_model(
        "read_file", "OPENAI_API_KEY=sk-rawsecret"
    )
    assert "sk-rawsecret" in out


def test_non_string_result_passes_through(agent):
    out = agent._tool_result_content_for_active_model("todo", {"ok": True})
    assert out == {"ok": True}
