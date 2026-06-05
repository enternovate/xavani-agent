# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R10 enforcement for the operator: decision modules make ZERO LLM calls
(v0.7.0 operator U6).

The operator's *decisions* — perceive, opportunity detection, ranking, tier
classification, state, config, verify-gating — are things the agent can do in
pure Python. They must never import or call a hosted model client, so the
always-on loop is cheap and the user is never billed tokens for the agent
*thinking*. The LLM is allowed in exactly one place: ``propose`` (generation),
which is deliberately excluded from this list.

Static AST + source check — fast, hermetic, makes no model calls itself. Mirrors
``tests/agent/test_deterministic_no_llm.py``. New deterministic modules MUST be
added here as the roadmap progresses (M1: perceive/opportunities/decide; M3:
verify/learn).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Operator modules that decide/route/govern and MUST stay LLM-free.
# NOTE: ``xavani_operator/propose.py`` is intentionally NOT here — it is the one
# generation surface where the LLM is allowed.
DETERMINISTIC_MODULES = [
    "xavani_operator/types.py",
    "xavani_operator/tiers.py",
    "xavani_operator/config.py",
    "xavani_operator/state.py",
    "xavani_operator/perceive.py",
    "xavani_operator/opportunities.py",
    "xavani_operator/decide.py",
    "xavani_operator/workstreams/base.py",
    # Even propose — the LLM *seam* — imports no client itself: the model is
    # always supplied via an injected `generate` callable (U35). This locks the
    # invariant that the operator package never hardcodes a model client.
    "xavani_operator/propose.py",
    "xavani_operator/approval_queue.py",
    "xavani_operator/audit.py",
    "xavani_operator/notify.py",
    "xavani_operator/act.py",
    "xavani_operator/verify.py",
    "xavani_operator/report.py",
    "xavani_operator/learn.py",
    "xavani_operator/loop.py",
    "xavani_operator/workstreams/build.py",
    # Even the real effectors hardcode no model client — the code agent is injected.
    "xavani_operator/workstreams/build_effectors.py",
]

FORBIDDEN_IMPORT_ROOTS = {
    "openai",
    "anthropic",
    "litellm",
    "cohere",
    "mistralai",
    "groq",
    "together",
}
FORBIDDEN_IMPORT_SUBSTRINGS = (
    "openrouter_client",
    "xai_http",
    "generativeai",
)
FORBIDDEN_CALL_SUBSTRINGS = (
    ".chat.completions",
    ".messages.create",
    "acompletion(",
    "completion.create",
)


def _imported_module_paths(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


@pytest.mark.parametrize("rel", DETERMINISTIC_MODULES)
def test_no_llm_client_in_operator_decision_module(rel: str) -> None:
    path = REPO / rel
    assert path.exists(), f"{rel} is missing — update DETERMINISTIC_MODULES"

    for module in _imported_module_paths(path):
        root = module.split(".")[0]
        assert root not in FORBIDDEN_IMPORT_ROOTS, (
            f"{rel} imports LLM client '{module}' — violates R10 "
            f"(operator decisions must be deterministic / no token cost)"
        )
        assert not any(s in module for s in FORBIDDEN_IMPORT_SUBSTRINGS), (
            f"{rel} imports model-client module '{module}' — violates R10"
        )

    src = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_CALL_SUBSTRINGS:
        assert pattern not in src, (
            f"{rel} contains model-call pattern '{pattern}' — violates R10"
        )
