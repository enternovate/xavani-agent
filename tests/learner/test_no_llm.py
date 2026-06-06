# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R10 for the learning/taste layer: selection + distillation hardcode no model
client (v0.7.0 operator L11).

The model only ever enters via an *injected* ``extract`` callable in
``style_learn`` — never imported by these modules. Style selection, the
anti-generic guardrail, taste recall, and preference capture are pure Python, so
'defaulting to learned taste' costs zero tokens. Static AST/source check mirroring
``tests/agent/test_deterministic_no_llm.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

LEARNER_MODULES = [
    "xavani_learner/style_profile.py",
    "xavani_learner/anti_generic.py",
    "xavani_learner/taste.py",
    "xavani_learner/preferences.py",
    "xavani_learner/style_learn.py",
    "xavani_learner/design_principles.py",
    "xavani_learner/design_review.py",
    "xavani_learner/design.py",
]

FORBIDDEN_IMPORT_ROOTS = {"openai", "anthropic", "litellm", "cohere", "mistralai", "groq", "together"}
FORBIDDEN_IMPORT_SUBSTRINGS = ("openrouter_client", "xai_http", "generativeai")
FORBIDDEN_CALL_SUBSTRINGS = (".chat.completions", ".messages.create", "acompletion(", "completion.create")


def _imported(path: Path) -> set[str]:
    mods: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


@pytest.mark.parametrize("rel", LEARNER_MODULES)
def test_learner_module_makes_no_llm_calls(rel: str) -> None:
    path = REPO / rel
    assert path.exists(), f"{rel} missing — update LEARNER_MODULES"
    for module in _imported(path):
        root = module.split(".")[0]
        assert root not in FORBIDDEN_IMPORT_ROOTS, f"{rel} imports LLM client '{module}' — violates R10"
        assert not any(s in module for s in FORBIDDEN_IMPORT_SUBSTRINGS), f"{rel} imports model client '{module}'"
    src = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_CALL_SUBSTRINGS:
        assert pattern not in src, f"{rel} contains model-call pattern '{pattern}' — violates R10"
