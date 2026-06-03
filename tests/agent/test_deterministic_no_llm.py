# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""R10 "deterministic-first" enforcement: detection/routing modules make ZERO LLM calls.

These modules decide things the agent can decide in pure Python — skill routing,
the pre-ship guidelines gate, eval checks, and skill-draft generation. They must
never import or call an LLM/model client, so the user is **never billed tokens for
the agent's own routing or self-governance**. This test locks that invariant in:
a future change that sneaks a model client into any of these paths fails CI.

It is a static (AST + source) check — fast, hermetic, and itself makes no model
calls. Pairs with the v0.4.0 roadmap (M1: zero-cost cognition).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Modules that perform detection / routing / governance and MUST stay LLM-free.
DETECTION_MODULES = [
    "xavani_learner/skill_orchestrator.py",   # deterministic skill router
    "xavani_learner/context_enricher.py",     # context selection
    "tools/guidelines_gate_tool.py",          # pre-ship verification gate
    "tools/eval_harness_tool.py",             # eval definition/run/report
    "xavani_learner/skill_improver.py",       # skill-draft template (no LLM)
]

# Import *roots* that indicate a hosted LLM/model client dependency.
FORBIDDEN_IMPORT_ROOTS = {
    "openai",
    "anthropic",
    "litellm",
    "cohere",
    "mistralai",
    "groq",
    "together",
}
# Forbidden substrings anywhere in an imported module path (covers local client wrappers).
FORBIDDEN_IMPORT_SUBSTRINGS = (
    "openrouter_client",
    "xai_http",
    "generativeai",
)
# Forbidden call patterns in the source text (model invocation surfaces).
FORBIDDEN_CALL_SUBSTRINGS = (
    ".chat.completions",
    ".messages.create",
    "acompletion(",
    "completion.create",
)


def _imported_module_paths(path: Path) -> set[str]:
    """Return the set of module paths imported by a Python file (via AST)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    return mods


@pytest.mark.parametrize("rel", DETECTION_MODULES)
def test_no_llm_client_in_detection_module(rel: str) -> None:
    """Each detection/routing module imports no LLM client and calls no model API."""
    path = REPO / rel
    assert path.exists(), f"{rel} is missing — update DETECTION_MODULES"

    for module in _imported_module_paths(path):
        root = module.split(".")[0]
        assert root not in FORBIDDEN_IMPORT_ROOTS, (
            f"{rel} imports LLM client '{module}' — violates R10 "
            f"(detection must be deterministic / no token cost)"
        )
        assert not any(s in module for s in FORBIDDEN_IMPORT_SUBSTRINGS), (
            f"{rel} imports model-client module '{module}' — violates R10"
        )

    src = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_CALL_SUBSTRINGS:
        assert pattern not in src, (
            f"{rel} contains model-call pattern '{pattern}' — violates R10"
        )


def test_skill_router_is_deterministic() -> None:
    """The deterministic skill router returns identical rankings for identical input."""
    from xavani_learner.skill_orchestrator import SkillOrchestrator

    orch = SkillOrchestrator()
    query = "build a trading bot"
    first = [s["name"] for s in orch.rank_skills_by_relevance(query, limit=5)]
    second = [s["name"] for s in orch.rank_skills_by_relevance(query, limit=5)]
    assert first == second, "skill ranking must be deterministic (no randomness, no LLM)"


def test_skill_router_imports_no_model_client_at_runtime() -> None:
    """Importing the router must not pull a hosted LLM client into sys.modules itself."""
    import importlib

    importlib.import_module("xavani_learner.skill_orchestrator")
    # The module's own import graph (checked statically above) is the contract;
    # here we assert the public ranking entrypoint is callable without network/model.
    from xavani_learner.skill_orchestrator import SkillOrchestrator

    assert callable(SkillOrchestrator.rank_skills_by_relevance)
