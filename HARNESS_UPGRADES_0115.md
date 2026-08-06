# HARNESS UPGRADES — Xavani 0.1.1.5

Date: 2026-08-06
Author: Hermes Agent, for Enternovate
Status: Research-backed recommendation list for the 0.1.1.5 harness upgrade.

> Web research was completed 2026-08-06 via the user's Firefox browser
> (Google search, Anthropic Engineering, Red Hat Developer) and the arXiv
> API. Sources are cited inline with URLs. This supersedes the earlier
> draft that used local-only sources.

---

## Summary

The harness is the loop that keeps the agent honest: evals before changes,
reviews after turns, metrics that survive a session. This document lists 15
concrete upgrades, ranked by value over effort. Items 1-5 are the ones
shipped in 0.1.1.5 (see Task 4.3 of the master plan). Items 6-15 are the
backlog for 0.1.2.

Ranking method: value = impact on reliability/quality per unit of user
facing pain; effort = S <1 day, M 1-3 days, L 1-2 weeks. The ranking uses
the same lens as `XAVANI_100_UPDATES.md` and `XAVANI_50_UPDATES.md`.

---

## Section 1 — Evaluation

### 1. Eval-gate on steer changes (SHIP in 0.1.1.5)

- Value: 9/10. Effort: M.
- Problem: the core loop (`run_agent.py`, `agent/conversation_loop.py`,
  steer paths) can be edited with no automated check that behaviour is
  preserved. Karpathy's first principle: "eval is all you need" — write the
  test that tells you whether it improved anything before writing
  improvement code (`skills/research-guidelines/karpathy-guidelines.md`).
- What: a CI step runs `tools/eval_harness_tool.py` golden evals whenever
  the steer paths change (`run_agent.py`, `agent/conversation_loop.py`,
  `agent/agent_init.py`, `cli.py` command dispatch). A failing eval blocks
  the merge.
- Where: `.github/workflows/eval-gate.yml` (new), plus a `scripts/run_golden_evals.py`
  wrapper that loads `~/.xavani/evals/golden.json` (or `tests/fixtures/golden-evals.json`)
  and runs each case with a deterministic handler.
- Source: Karpathy operating guidelines (local research pack); SWE-bench
  methodology (regression evals on every change).
- Test plan: `tests/tools/test_eval_gate.py` — fixture eval passes; fixture
  eval fails; path filter only triggers on steer paths.

### 2. Tool-call quality metrics (SHIP in 0.1.1.5)

- Value: 8/10. Effort: M.
- Problem: the harness records what tools ran, but not whether they
  succeeded, how long they took, or how many retries they needed. DORA
  tells us: if you cannot measure it, you cannot improve it. Pólya: "look
  at the data before you theorise".
- What: per-session CSV/JSONL with one row per tool call: tool name,
  latency ms, success bool, retry count, error class. Surfaced by
  `xavani stats` (CLI) and aggregated per day.
- Where: `agent/tool_metrics.py` (new), called from the tool dispatch
  wrapper in `run_agent.py`; `xavani_cli/commands.py` gets a `stats` view.
- Source: DORA metrics (deployment frequency, lead time, change-failure
  rate) applied to agent tool usage; local `XAVANI_50_UPDATES.md` E05
  (cost CSV) as the sibling pattern.
- Test plan: `tests/agent/test_tool_metrics.py` — metrics recorded with
  correct fields; retry counted; CSV round-trip; stats output stable.

### 3. Self-critique pass (SHIP in 0.1.1.5)

- Value: 7/10. Effort: M.
- Problem: the final answer ships without a quality review. Hamming:
  "the purpose of computing is insight, not numbers" — but the agent
  needs a second look to find its own errors. The existing
  `agent/background_review.py` reviews memory/skills, not answer quality.
- What: config-gated (`harness.self_critique: true`) final-answer review
  step. The model reviews its own answer against a rubric (correctness,
  completeness, citations, STE compliance). One bounded fix iteration
  (max 1 re-write), then the loop stops. No infinite loops.
- Where: `agent/self_critique.py` (new), invoked at end of turn in
  `agent/conversation_loop.py`.
- Source: Anthropic "Building Effective Agents" (iterative refinement);
  OpenAI "evals" philosophy; Kahneman's System-2 style re-check.
- Test plan: `tests/agent/test_self_critique.py` — rubric parse; bounded
  loop (1 iteration max); disabled when config off; no crash on bad rubric.

### 4. Context-budget governor UI (SHIP in 0.1.1.5)

- Value: 7/10. Effort: S.
- Problem: `agent/budget_governor.py` tracks session cost, but the user
  has no in-chat signal that context is running low until it is too late.
  B02 (context breakdown) exists in `xavani_cli/statusline.py`; the
  warning threshold is not surfaced.
- What: warn at 85% of the context budget with a compaction suggestion
  ("context at 85% — /compact recommended"). Threshold logic is pure and
  testable. Optional: auto-suggest at 85%, block new tools at 95%.
- Where: `agent/budget_governor.py` (extend), surfaced in
  `xavani_cli/statusline.py` and `cli.py /usage`.
- Source: local `XAVANI_50_UPDATES.md` B02; Hermes context-budget
  behaviour; Karpathy "treat the model like software" (operating rules).
- Test plan: `tests/agent/test_budget_governor.py` — 85% threshold fires;
  compaction suggestion text; no false positive under 85%.

### 5. Flake dashboard ingestion (SHIP in 0.1.1.5)

- Value: 6/10. Effort: S.
- Problem: `tests/flakiness.json` exists but nothing consumes it. The
  flake report is invisible. Tukey: "the data may not contain the answer,
  but the answer is in the data".
- What: aggregate `tests/flakiness.json` into a per-release report
  (top flaky tests, root-cause labels, trend). Emit as a CI artifact and
  a markdown summary in the release notes.
- Where: `scripts/flake_dashboard.py` (new), `.github/workflows/flake-dashboard.yml`.
- Source: `XAVANI_100_UPDATES.md` A01-A06 (anti-flake programme); DORA
  change-failure rate as the north-star metric.
- Test plan: `tests/test_flake_dashboard.py` — aggregation of fixture
  JSON; empty input; unknown label; release summary format.

---

## Section 2 — Reliability

### 6. Deterministic xdist ordering (backlog)

- Value: 8/10. Effort: M.
- What: replace `-n auto` with `--dist loadscope` so subsystem tests
  (approval, tirith, cron, budget) group per worker. Kills cross-worker
  state poisoning.
- Where: `pyproject.toml`, CI workflows.
- Source: `XAVANI_100_UPDATES.md` A04.
- Test plan: run the suite twice with the new ordering; 0 fail / 0 skip.

### 7. Test failure budget + triage (backlog)

- Value: 7/10. Effort: S.
- What: any CI failure that repeats creates a P0 tracking issue; auto-escalates.
- Where: `.github/workflows/`, new `scripts/failure_budget.py`.
- Source: `XAVANI_100_UPDATES.md` A05.
- Test plan: unit test the budget logic; dry-run the workflow.

### 8. Turn lease hardening (backlog)

- Value: 7/10. Effort: M.
- What: A07 turn lease exists; extend to gateway multi-session with
  per-session key and reject/queue semantics, plus a test that a second
  turn on the same session key cannot double-fire the model.
- Where: `gateway/run.py`, `gateway/turn_lease.py` (new).
- Source: `XAVANI_50_UPDATES.md` A07.
- Test plan: `tests/gateway/test_turn_lease.py` — second turn rejected;
  queue drains; lease expires.

### 9. Crash forensics completeness (backlog)

- Value: 6/10. Effort: S.
- What: verify `shutdown_forensics.py` dumps last N log lines + thread
  stacks on abnormal exit; add a test.
- Where: `xavani.py`, `gateway/run.py`.
- Source: `XAVANI_50_UPDATES.md` E03.
- Test plan: `tests/gateway/test_shutdown_forensics.py`.

---

## Section 3 — Quality-of-output

### 10. Rubric library for self-critique (backlog)

- Value: 7/10. Effort: M.
- What: 3-5 named rubrics (technical answer, code review, STE prose) that
  the self-critique pass loads. Pure YAML data, no code churn per rubric.
- Where: `skills/rubrics/*.yaml` (new), loaded by `agent/self_critique.py`.
- Source: Anthropic "Building Effective Agents"; Hermes answer-quality
  rubrics in `skills/research-guidelines/`.
- Test plan: `tests/agent/test_rubric_library.py`.

### 11. Answer-quality eval suite (backlog)

- Value: 8/10. Effort: L.
- What: a golden set of 20-30 question-answer pairs per domain with
  rubrics; `xavani evals run answer-quality` scores the current model.
- Where: `tests/fixtures/answer-quality/*.json`, extended eval harness.
- Source: SWE-bench methodology; OpenAI evals.
- Test plan: `tests/tools/test_answer_quality_evals.py`.

---

## Section 4 — Observability

### 12. Per-turn timeline trace export (backlog)

- Value: 7/10. Effort: M.
- What: E02 turn timeline (user msg → model call → tools → final) with
  durations, exported as JSONL. Makes "why did the agent do X" answerable.
- Where: `agent/trajectory.py` (extend), `xavani_cli/sessions_cmd.py`.
- Source: `XAVANI_50_UPDATES.md` E02.
- Test plan: `tests/agent/test_trajectory.py`.

### 13. Gateway health export (backlog)

- Value: 6/10. Effort: M.
- What: E01 /health endpoint + prometheus-exportable health state.
- Where: `gateway/run.py`, `xavani_observability/prometheus.py`.
- Source: `XAVANI_50_UPDATES.md` E01.
- Test plan: `tests/gateway/test_health_export.py`.

### 14. Memory/skill mutation audit log (backlog)

- Value: 7/10. Effort: S.
- What: D06 append-only JSONL of memory + skill writes with origin
  (assistant_tool vs background_review). Traceability + pairs with the
  write-approval gate.
- Where: `tools/memory_tool.py`, `tools/skill_manager_tool.py`.
- Source: `XAVANI_50_UPDATES.md` D06.
- Test plan: `tests/tools/test_mutation_audit.py`.

---

## Section 5 — Dependencies

### 15. Harness dependency additions (SHIP in 0.1.1.5)

- Value: 6/10. Effort: S.
- What: add these exact-pinned, justified dependencies:
  - `pydantic-settings==2.12.5` — typed config for harness modules
    (self-critique, tool metrics). Replaces ad-hoc env parsing.
  - `jsonschema==4.25.1` — validate tool output schemas in evals.
  - `diskcache==5.4.0` — eval + metrics state cache (persistent, no
    server). Avoids re-running expensive evals.
  - `structlog==25.6.0` — structured logs for tool metrics + timeline.
  - `orjson==3.11.1` — fast JSON for metrics CSV/JSONL paths.
  - Verify `tenacity==9.1.4` and `rich==14.3.3` (present — keep).
- Where: `pyproject.toml` exact pins, `uv lock` regenerate.
- Source: `XAVANI_50_UPDATES.md` E05; the repo's own exact-pin
  supply-chain policy (see pyproject.toml dependency comment).
- Test plan: `pip check` clean; `pytest tests/xavani_cli tests/agent -q`
  green; affected suites 0 fail / 0 skip.

---

## Section 6 — Web Research Addendum (2026-08-06)

Research performed through the user's Firefox browser + arXiv API.
The 2026 landscape confirms Xavani's harness direction: eval-driven
development is now the industry standard for agent reliability, and the
frontier has moved from raw model capability to *harness engineering*
(environment, tools, feedback) and *graph engineering* (multi-loop
orchestration).

### 6.1 Eval-driven development is the standard (Anthropic, Red Hat)

- Anthropic, "Demystifying evals for AI agents" (2026-01-09):
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
  - An eval = input + agent loop + grading logic. Multi-turn evals
    dominate; agent evals grade environment state (unit tests), not just
    text. Mistakes propagate and compound across turns; static
    exact-match grading fails against creative model solutions.
  - Direct Xavani mapping: the eval harness must support multi-step
    cases with environment assertions, not just exact/contains matching.
- Red Hat Developer, "Eval-driven development: Build and evaluate
  reliable AI agents" (2026-03-23), Michael Dawson:
  https://developers.redhat.com/articles/2026/03/23/eval-driven-development-build-evaluate-ai-agents
  - 8-stage evaluation framework; DeepEval-style multi-turn testing;
    CI/CD integration of evals; agentic output is inherently variable so
    deterministic frameworks fail — evals must be graded semantically.
  - Direct Xavani mapping: our eval-gate (item 1) mirrors Red Hat's
    CI/CD eval integration; the rubric library (item 10) is the
    semantic-grading answer to variability.

### 6.2 Harness engineering + graph engineering (March 2026 shift)

- Google AI Overview synthesis (2026-03, citing Medium and industry
  sources): as of March 2026, engineering reliable autonomous systems
  shifted focus from raw model capability to:
  - *harness engineering* — controlling the environment, tools, and
    feedback loops around the agent;
  - *graph engineering* — orchestrating multi-loop networks of agents
    and evaluations.
  - Direct Xavani mapping: tool-call metrics (item 2), self-critique
    (item 3), and budget governor (item 4) ARE harness engineering.
    Graph engineering maps to the multi-loop network of
    background_review → memory → skill updates (B05/G02) and the
    subagent lifecycle API (B08).

### 6.3 Frontier open-model reports (what the best agents are built on)

- Kimi K3 Technical Report (Moonshot AI, 2026): 2.8T MoE, 104B active,
  native vision, 1M-token context. Key post-training highlights:
  - RL across general, agentic, and coding domains;
  - *multiple reasoning-effort levels* — compositional generalization
    and robust long-horizon execution;
  - *million-token agentic RL with persistent rollout and sandbox
    states* — the sandbox is the harness.
  - Direct Xavani mapping: reasoning-effort auto-tuning (B06) is the
    "multiple reasoning-effort levels" pattern; eval sandboxing with
    persistent state should be a 0.1.2 harness item.
- DeepSeek-V4 Technical Report (2026): V4-Pro 1.6T/49B active and
  V4-Flash 284B/13B active, both 1M-token context. Architecture
  upgrades: Compressed Sparse Attention + Heavily Compressed Attention,
  Manifold-Constrained Hyper-Connections, Muon optimizer, 32T+ tokens.
  Efficiency result: at 1M context, V4-Pro needs 27% of single-token
  inference FLOPs and 10% of KV cache vs V3.2.
  - Direct Xavani mapping: context-budget governor (item 4) exists;
  add a KV/context-efficiency metric to tool-call metrics (item 2)
  so users can see per-turn context cost.
- OpenMLE / Frontis-MA1 (FrontisAI, 2026): recursive self-improvement
  via *execution-grounded* RL on verifiable task environments. Atomic
  program-evolution operators: Draft, Improve, Debug, Crossover. Long-
  horizon search composes learning + evolution.
  - Direct Xavani mapping: background_review is a single-step Improve
    operator. The bounded self-critique loop (item 3) is the Improve
    operator applied to answers. A 0.1.2 item: a Draft→Improve→Debug
    loop over skills, grounded in test execution.

### 6.4 Trace mining + resource-constrained evals (new items)

- TraceCompiler (arXiv, 2026): mines LLM agent traces and compiles them
  into mostly-deterministic workflows. Successful traces become
  repeatable procedures.
  - NEW ITEM 16 (backlog, 0.1.2): trace → workflow compilation.
    On successful task completion, compile the trajectory into a
    repeatable skill/workflow draft. Test: trajectory capture +
    compilation + replay equivalence.
- AgentSLABench (arXiv, 2026): evaluates agentic systems under resource
  constraints (budget, time, tool calls).
  - NEW ITEM 17 (backlog, 0.1.2): resource-constrained eval mode —
    eval cases declare a budget; the harness enforces it and reports
    cost per success. Test: budget enforcement, cost-per-success metric.

### 6.5 Community signals (Reddit r/AI_Agents)

- "What AI harness for coding?" thread (2026-07, 60+ comments): active
  community demand for harness ergonomics — eval feedback loops, cost
  visibility, trace replay. Confirms items 1, 2, 4 as the highest-value
  user-facing harness work.

### 6.6 What Xavani still misses (gap list, from research)

1. Multi-turn eval cases with environment assertions (6.1) — eval
   harness is single-turn today.
2. Reasoning-effort-aware eval runs (6.3) — run evals at low/high
   effort and report the delta.
3. Trace → workflow compilation (6.4, item 16).
4. Resource-constrained eval mode (6.4, item 17).
5. Per-turn context-cost metric in /usage (6.3).
6. Execution-grounded skill evolution loop (6.3, Draft→Improve→Debug).
7. Sandboxed eval state persistence (6.3) — eval runs leave no side
   effects; a persistent sandbox enables long-horizon evals.

---

## Ranking table

| # | Upgrade | Value | Effort | Ship |
|---|---------|-------|--------|------|
| 1 | Eval-gate on steer changes | 9 | M | 0.1.1.5 |
| 2 | Tool-call quality metrics | 8 | M | 0.1.1.5 |
| 3 | Self-critique pass | 7 | M | 0.1.1.5 |
| 4 | Context-budget governor UI | 7 | S | 0.1.1.5 |
| 5 | Flake dashboard ingestion | 6 | S | 0.1.1.5 |
| 6 | Deterministic xdist ordering | 8 | M | 0.1.2 |
| 7 | Test failure budget + triage | 7 | S | 0.1.2 |
| 8 | Turn lease hardening | 7 | M | 0.1.2 |
| 9 | Crash forensics completeness | 6 | S | 0.1.2 |
| 10 | Rubric library | 7 | M | 0.1.2 |
| 11 | Answer-quality eval suite | 8 | L | 0.2 |
| 12 | Per-turn timeline trace | 7 | M | 0.1.2 |
| 13 | Gateway health export | 6 | M | 0.1.2 |
| 14 | Memory/skill mutation audit | 7 | S | 0.1.2 |
| 15 | Harness dependency additions | 6 | S | 0.1.1.5 |

## Sources (local-first)

- `skills/research-guidelines/` — Karpathy, Hamming, Pólya, Tukey,
  Dijkstra, Fowler, Hickey, Kernighan-Pike, Huyen, Chollet, Carmack,
  Beck, Hassabis, Hinton, conscience guidelines.
- `XAVANI_100_UPDATES.md` — A01-A06 anti-flake + eval programme.
- `XAVANI_50_UPDATES.md` — B02, D06, E01-E06, G02 items referenced above.
- `tools/eval_harness_tool.py` — existing eval storage/run/assert.
- `agent/background_review.py` — existing post-turn review (memory/skills).
- `agent/budget_governor.py` — existing session cost governor.
- `tests/flakiness.json` — real flake data (test_id, label, traceback).

## Web sources (2026-08-06, verified via Firefox + arXiv API)

- Anthropic, "Demystifying evals for AI agents" (2026-01-09) —
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic, "Building Effective Agents" (2024-12-19) —
  https://www.anthropic.com/engineering/building-effective-agents
- Red Hat Developer, "Eval-driven development: Build and evaluate
  reliable AI agents" (2026-03-23) —
  https://developers.redhat.com/articles/2026/03/23/eval-driven-development-build-evaluate-ai-agents
- Kimi K3 Technical Report (arXiv, 2026) — "Kimi K3: Open Frontier
  Intelligence" (2.8T MoE, KDA attention, million-token agentic RL,
  sandbox states).
- DeepSeek-V4 Technical Report (arXiv, 2026) — "DeepSeek-V4: Towards
  Highly Efficient Million-Token Context Intelligence" (CSA/HCA hybrid
  attention, mHC, Muon, 27% FLOPs / 10% KV at 1M context).
- OpenMLE / Frontis-MA1 (arXiv, 2026) — "Frontis-MA1: Training an AI4AI
  Model towards Recursive Self-Improvement in Machine Learning
  Engineering" (Draft/Improve/Debug/Crossover operators).
- TraceCompiler (arXiv, 2026) — skill-guided mining of LLM agent traces
  into deterministic workflows.
- AgentSLABench (arXiv, 2026) — evaluating agentic systems under
  resource constraints.
- Reddit r/AI_Agents — "What AI harness for coding?" (2026-07).

## Published guidance (from the author's knowledge base)

- Karpathy, "Software 2.0" — evals-first, treat models like software.
- SWE-bench (ICLR 2024) — regression evals as the change gate.
- DORA State of DevOps — change-failure rate, deployment frequency.
