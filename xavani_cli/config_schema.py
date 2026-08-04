# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Typed JSON Schema (draft-07) for the main ``config.yaml`` sections.

Covers only the core sections (``agent``, ``model``, ``memory``,
``toolsets``, ``gateway``) plus the root shape.  Unknown keys are allowed
(``additionalProperties: true``) so the schema stays useful as the config
grows — it is a *sanity* contract, not an exhaustive spec.
"""

from __future__ import annotations

from typing import Any, Dict, List

CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://xavani.dev/schemas/config.schema.json",
    "title": "Xavani config.yaml",
    "description": "Core sections of the Xavani agent configuration file.",
    "type": "object",
    "properties": {
        "model": {
            "type": "object",
            "description": "Default model, provider, and wire protocol.",
            "properties": {
                "default": {"type": "string", "minLength": 1},
                "provider": {"type": "string", "minLength": 1},
                "base_url": {"type": "string"},
                "api_mode": {
                    "type": "string",
                    "enum": [
                        "chat_completions",
                        "responses",
                        "anthropic_messages",
                        "codex_responses",
                        "gemini",
                    ],
                },
            },
            "additionalProperties": True,
        },
        "agent": {
            "type": "object",
            "description": "Agent loop behaviour and timeouts.",
            "properties": {
                "max_turns": {"type": "integer", "minimum": 1},
                "gateway_timeout": {"type": "integer", "minimum": 0},
                "restart_drain_timeout": {"type": "integer", "minimum": 0},
                "api_max_retries": {"type": "integer", "minimum": 0},
                "service_tier": {"type": "string"},
                "gateway_timeout_warning": {"type": "integer", "minimum": 0},
                "clarify_timeout": {"type": "integer", "minimum": 0},
                "gateway_notify_interval": {"type": "integer", "minimum": 0},
                "gateway_auto_continue_freshness": {"type": "integer", "minimum": 0},
                "image_input_mode": {"type": "string"},
                "disabled_toolsets": {"type": "array", "items": {"type": "string"}},
                "tool_use_enforcement": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "boolean"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
            },
            "additionalProperties": True,
        },
        "memory": {
            "type": "object",
            "description": "Built-in memory and user profile settings.",
            "properties": {
                "memory_enabled": {"type": "boolean"},
                "user_profile_enabled": {"type": "boolean"},
                "memory_char_limit": {"type": "integer", "minimum": 0},
                "user_char_limit": {"type": "integer", "minimum": 0},
                "provider": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "toolsets": {
            "type": "array",
            "description": "Toolset names to enable (e.g. xavani-cli, web, browser).",
            "items": {"type": "string", "minLength": 1},
        },
        "gateway": {
            "type": "object",
            "description": "Gateway server behaviour (proxy URL, streaming, …).",
            "properties": {
                "proxy_url": {"type": "string"},
                "streaming": {"type": "boolean"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}


def validate_config_schema(config: Any) -> List[str]:
    """Validate a parsed ``config.yaml`` against :data:`CONFIG_SCHEMA`.

    Returns a list of human-readable error strings.  An empty list means
    the config conforms.  ``jsonschema`` is imported lazily so modules that
    only need the schema dict don't pay the import cost.
    """
    if not isinstance(config, dict):
        return ["config.yaml must be a YAML mapping at the top level"]

    import jsonschema

    errors: List[str] = []
    for err in sorted(
        jsonschema.Draft7Validator(CONFIG_SCHEMA).iter_errors(config),
        key=lambda e: list(e.absolute_path or []),
    ):
        path = ".".join(str(p) for p in (err.absolute_path or [])) or "(root)"
        errors.append(f"{path}: {err.message}")
    return errors
