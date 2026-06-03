# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the deterministic detector registry (v0.4.0 U9)."""

from __future__ import annotations

import ast
import inspect

from agent import detectors


def test_builtin_detectors_registered():
    assert {"scrub", "stub_guard", "secret_leak"} <= set(detectors.names())


def test_scrub_detector_flags_upstream_reference():
    bad = detectors.run("scrub", {"text": "this was built on Nous Research's hermes-agent"})
    assert bad.ok is False and bad.findings
    good = detectors.run("scrub", {"text": "Xavani Agent by Enternovate — local and private"})
    assert good.ok is True and not good.findings


def test_stub_guard_flags_stub_edit():
    diff = "diff --git a/tools/skills_hub.py b/tools/skills_hub.py\n+def crawl(): ..."
    v = detectors.run("stub_guard", {"diff": diff})
    assert v.ok is False and v.findings
    clean = detectors.run("stub_guard", {"diff": "diff --git a/tools/foo.py b/tools/foo.py\n+x=1"})
    assert clean.ok is True


def test_secret_leak_detector():
    leak = detectors.run("secret_leak", {"text": "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz0123"})
    assert leak.ok is False and leak.findings
    clean = detectors.run("secret_leak", {"text": "no secrets here"})
    assert clean.ok is True


def test_run_all_returns_all_verdicts_and_is_ok_for_clean_context():
    verdicts = detectors.run_all({"text": "clean", "diff": ""})
    assert len(verdicts) == len(detectors.names())
    assert all(v.ok for v in verdicts)


def test_unknown_detector_raises():
    import pytest

    with pytest.raises(KeyError):
        detectors.run("does-not-exist", {})


def test_detectors_module_is_llm_free():
    tree = ast.parse(inspect.getsource(detectors))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq"})
