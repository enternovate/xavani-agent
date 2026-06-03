<!-- Project rule doc (NOT a thinker guideline). Filename deliberately avoids the
     `*-guidelines.md` glob so the research-guidelines loader does not auto-inject it
     and the 21-thinker test contract is unaffected. Enforcement is automated by
     tests/agent/test_deterministic_no_llm.py, not by prompt injection. -->

# R10 — Deterministic-First (zero-cost cognition)

**Rule:** The LLM is for *generation only*. Never spend an LLM/API call on anything
the agent can decide in pure Python — **routing, detection, matching, filtering, or
self-governance**. Doing so bills the user tokens for work that costs nothing locally.

## Why
Every avoided model round-trip is money and latency saved for the user. Detection and
routing are deterministic problems; treat them as such.

## What must stay deterministic (pure Python, no model client)
| Concern | Implementation |
|---|---|
| Skill routing | `xavani_learner/skill_orchestrator.py` (`SkillOrchestrator.rank_skills_by_relevance`) |
| Tool dispatch | `model_tools.handle_function_call` → `tools/registry.py::registry.dispatch` |
| Per-turn tool pre-filter | `tools/tool_prefilter.py` (`select_tools` / `filter_definitions`) |
| Pre-ship gate | `tools/guidelines_gate_tool.py` |
| Eval checks | `tools/eval_harness_tool.py` |
| Skill-draft generation | `xavani_learner/skill_improver.py` (template, not LLM) |

## How it is enforced (not by reminder)
- `tests/agent/test_deterministic_no_llm.py` statically asserts these modules import
  **no** model client (`openai`, `anthropic`, `litellm`, `openrouter_client`, …) and
  contain **no** model-call patterns (`.chat.completions`, `.messages.create`, …).
- `tests/tools/test_tool_prefilter.py` asserts the pre-filter is LLM-free and deterministic.
- A change that introduces a model call into any detection/routing path fails CI.

## When adding new behavior
1. If it *decides* something (which skill, which tool, is-this-allowed, did-this-pass) →
   implement it in Python and add it to the enforced module list above.
2. Only reach for the model when you must *generate* novel content the rules can't produce.
3. Prefer shrinking what is sent to the model (see `tool_prefilter`) over sending everything.
