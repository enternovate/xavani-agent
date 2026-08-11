# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the network egress allowlist (v0.4.0 U42)."""

from __future__ import annotations

import ast
import inspect

import pytest

from tools.egress_policy import EgressBlocked, EgressPolicy, from_env

pytestmark = pytest.mark.unit


def test_allowlist_matches_host_and_subdomain():
    p = EgressPolicy.create(allow=["example.com", "openai.com"], default_deny=True)
    assert p.is_allowed("https://example.com/path")[0] is True
    assert p.is_allowed("https://api.example.com")[0] is True          # subdomain
    assert p.is_allowed("example.com")[0] is True                      # bare host
    assert p.is_allowed("https://evil.com")[0] is False
    assert p.is_allowed("https://notexample.com")[0] is False          # not a subdomain


def test_default_allow_when_default_deny_off():
    p = EgressPolicy.create(allow=[], default_deny=False)
    assert p.is_allowed("https://anything.test")[0] is True


def test_default_deny_blocks_everything_not_listed():
    p = EgressPolicy.create(allow=[], default_deny=True)
    assert p.is_allowed("https://anything.test")[0] is False


def test_check_raises_when_blocked():
    p = EgressPolicy.create(allow=["good.com"], default_deny=True)
    assert p.check("https://good.com/x") is True
    with pytest.raises(EgressBlocked):
        p.check("https://bad.com")


def test_from_env_parses_allowlist_and_default_deny():
    env = {
        "XAVANI_EGRESS_ALLOWLIST": "api.example.com, example.org  pypi.org",
        "XAVANI_EGRESS_DEFAULT_DENY": "true",
    }
    p = from_env(env)
    assert p.default_deny is True
    assert p.is_allowed("https://example.org")[0] is True
    assert p.is_allowed("https://files.pypi.org")[0] is True
    assert p.is_allowed("https://malware.test")[0] is False


def test_from_env_defaults_to_allow():
    p = from_env({})
    assert p.default_deny is False
    assert p.is_allowed("https://anything.test")[0] is True


def test_egress_policy_is_llm_free():
    import tools.egress_policy as m

    tree = ast.parse(inspect.getsource(m))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq"})
