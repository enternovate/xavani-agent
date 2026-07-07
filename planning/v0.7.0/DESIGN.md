<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Design spec for the autonomy layer ("Xavani Operator").
     Authored after the v0.6.0 release; pairs with planning/v0.7.0/ROADMAP.md. Keep untracked
     (do not `git add`) unless the user decides to commit. The USER controls all pushes. -->

# Xavani Operator — Autonomy Layer Design (v0.7.0 → v0.9.0)

> **Approved direction (brainstorm, 2026-06-04):** full operator that **builds + promotes** a
> plugged-in product, on a **general engine**, with **tiered approval** ("it initiates, I just
> approve"), reading a **repo + `xavani.product.yaml`**. Built as an **OODA Operator engine**;
> a durable DAG layer folds in mid-roadmap, multi-agent teams near the end.

## 1. Vision

Plug Xavani into a product (a repo + a `product.yaml`). It runs a continuous, deterministic
control loop: it **perceives** the product's state, **decides** what is most worth doing,
**proposes** a concrete plan, waits for the user to **approve**, then **acts** (full-stack build
*and* promotion), **verifies**, **reports**, and **learns**. The user never has to say "do X" —
they review proposals and approve. Cost stays low because every *decision* is pure Python; the LLM
is used only to *generate* the things a human would (plans, code, copy).

## 2. Architecture — `xavani_operator/` (new top-level package)

Sibling to `xavani_memory/`, `xavani_observability/`. Every new `.py` carries the Enternovate
header (R8) and a docstring naming its roadmap update (e.g. "v0.7.0 operator U12").

| Module | Purpose | LLM? |
|---|---|---|
| `config.py` | Load + validate `xavani.product.yaml` (pydantic v2) | ✗ |
| `state.py` | Persistent operator state under `~/.xavani/operator/` (cycles, proposals, tasks) | ✗ |
| `perceive.py` | Gather signals: git status, failing tests, TODO/issues, CI, metrics, channel inbox, last cycle | ✗ |
| `opportunities.py` | Deterministic rules: perception → ranked candidate goals (Opportunity objects) | ✗ |
| `decide.py` | Select top opportunities under budget/constraints → an Intent | ✗ |
| `propose.py` | Turn Intent + context into a concrete **Proposal** (steps, diffs, drafts) | ✓ generate-only |
| `approval_queue.py` | Queue of proposals; tier classification; reuses `tools/approval.py` | ✗ |
| `act.py` | Execute approved plan steps via existing tools/subagents | ✗ (dispatch) |
| `verify.py` | Post-conditions: tests, lint, smoke, content/brand checks, dry-runs | mostly ✗ |
| `report.py` | Cycle report → deliver via gateway/CLI | ✗ |
| `learn.py` | Outcomes → memory/insights; update opportunity weights deterministically | ✗ |
| `loop.py` | Orchestrate Perceive→…→Learn; single-cycle or continuous | ✗ |
| `tiers.py` | Pure action-class → tier classifier (0 Auto / 1 Notify / 2 Approve / 3 Block) | ✗ |
| `workstreams/base.py` | `Workstream` protocol | — |
| `workstreams/build.py` | Software lifecycle pack (plan → full-stack implement → test → ship) | mixed |
| `workstreams/promote.py` | Growth pack (content → schedule → multi-channel outreach → analytics) | mixed |
| `workstreams/ops.py` | Operations pack (deps, security scans, monitoring, housekeeping) | ✗-leaning |

**`Workstream` protocol** (one clear interface so packs are independently testable):
```python
class Workstream(Protocol):
    name: str
    def detect_opportunities(self, perception: Perception) -> list[Opportunity]: ...   # deterministic
    def make_plan(self, intent: Intent, ctx: Context) -> Proposal: ...                 # LLM generate-only
    def execute(self, step: PlanStep, ctx: Context) -> StepResult: ...                 # dispatch
    def verify(self, result: StepResult, ctx: Context) -> Verdict: ...                 # deterministic-leaning
```

## 3. Control loop

```
            ┌─────────── continuous / cron trigger ───────────┐
            ▼                                                  │
 Perceive → Opportunities → Decide → Propose ──► Approval Queue (tiered)
   (det)        (det)        (det)    (LLM gen)        │ user approves
                                                       ▼
                              Learn ◄─ Report ◄─ Verify ◄─ Act
                              (det)     (det)     (det)   (dispatch)
```
- Single cycle: `xavani operator cycle` (one Perceive→…→Learn pass; stops at the approval gate).
- Continuous: `xavani operator run` (loops on a cadence from `schedule.cycle_cadence`, honoring
  budgets, quiet hours, and the iteration/budget governors).
- Every long run is checkpointed (`tools/checkpoint_manager.py`) so it resumes after interruption.

## 4. Tiered approval ("I just approve")

| Tier | Examples | Behavior |
|---|---|---|
| **0 Auto** | read repo, run tests/lint, draft to staging, commit to a work branch | runs silently, logged |
| **1 Notify** | open *draft* PR, create issue, stage content | runs, pings user, veto window |
| **2 Approve** | merge/deploy, **post to a platform**, spend > threshold, external send, delete | blocks for explicit approval |
| **3 Block** | force-push, prod data ops, payments | per-action confirm, always |

The agent proposes a **whole plan**, each step tagged by tier. The user approves the plan once →
Tier 0/1 steps run; Tier 2 steps listed in the approved plan are pre-authorized by that approval;
**Tier 3 always re-confirms** at execution. All tiers overridable per action-class in
`approval.tier_overrides`. Defaults are conservative. Reuses `tools/approval.py`,
`tools/slash_confirm.py`, `tools/interrupt.py`.

## 5. `xavani.product.yaml`

```yaml
product:    { name, description, repo, stack }
goals:      [ {id, intent, priority, success_metric} ]      # ranked objectives
channels:   [ {platform: x|discord|telegram|email|blog, handle, cadence} ]
brand:      { voice, tone, dos, donts, assets }
constraints:{ no_touch_paths, allowed_actions, content_policy }
budgets:    { llm_tokens_per_day, spend_per_day, max_actions_per_cycle }
approval:   { tier_overrides, auto_window, quiet_hours }
schedule:   { cycle_cadence (cron), watchers }
```
Validated by `config.py` (pydantic v2). Missing optional sections get safe defaults. The loader
emits actionable errors; `xavani operator init` scaffolds a starter file.

## 6. Determinism & cost (R10 — the spine)

Perceive, opportunity detection, decide/rank, tier classification, and verification gating are
**pure Python — zero model calls**, unit-tested to make zero model-client calls (same harness as
the existing `tests/agent/test_detectors_no_llm.py`). The LLM runs **only** in `propose.make_plan`
(generate plan/code/content) and optional `verify` critique. The always-on loop is cheap; cost
scales with *approved generation*, not with thinking. `xavani operator status --savings` surfaces
LLM calls avoided (extends the existing avoided-cost telemetry).

## 7. Reuse map (build on primitives, don't reinvent)

| Need | Existing module |
|---|---|
| Approval / HITL | `tools/approval.py`, `slash_confirm.py`, `clarify_tool.py`, `interrupt.py` |
| Subagents / parallel | `tools/delegate_tool.py` |
| Scheduling / triggers | `tools/cronjob_tools.py`, `agent/curator_backup.py` (cron store) |
| Tasks / decomposition | `xavani_cli/goals.py`, `xavani_cli/kanban*.py`, `tools/kanban_tools.py`, `todo_tool.py` |
| Checkpoint / resume | `tools/checkpoint_manager.py` |
| Budget / cost | `agent/budget_governor.py`, `iteration_budget.py`, `account_usage.py` |
| Memory / learn | `xavani_memory/`, `agent/insights.py`, `curator.py`, `background_review.py` |
| Promote channels | `gateway/platforms/*` + `image_generation_tool`, `video_generation_tool`, `document_tools`, `web_tools` |
| Deterministic detection | `agent/detectors.py`, `agent/skill_router.py`, `tools/tool_prefilter.py` |

## 8. House rules (carried from the v0.3.1→v0.6.0 roadmap)

- **R1 Scrub:** no new `nous`/`hermes` references in shipped artifacts.
- **R2 Stubs:** never touch `tools/skills_hub.py` / `gateway/platforms/weixin.py` bodies or test skips.
- **R3 Xavani-native:** re-implement; never copy upstream code/names.
- **R4 Surgical diffs. R5 Tests for every change; `pytest -q` green; no new skips.**
- **R7 Identity:** don't alter `default_soul.py`/`prompt_builder.py` except to append.
- **R8 Enternovate header on every new `.py`.**
- **R9 Version:** bump once per milestone in `pyproject.toml` + `xavani_cli/__init__.py` + `xavani.py`.
- **R10 Deterministic-first:** never spend an LLM call on detection/routing/governance.
- **NO PUSH by the agent. The user controls all commits/pushes.** Interpreter is `python3`.

## 9. Definition of Done (per milestone)

```
python3 -m pytest -q                          # full suite green, no new skips (R5)
python3 -m pytest -k "operator and no_llm"    # R10: operator decision path makes ZERO model calls
python3 -c "import xavani_operator; print('OK')"
grep -rniE '\b(nous|hermes)\b' <changed files># only existing attribution (R1)
git status --porcelain | grep -E "skills_hub|weixin|default_soul" && echo VIOLATION || echo OK
```
Each update is one small change + its tests + its Verify. Milestones are independently releasable.
If an item can't be done safely, STOP and leave a precise `TODO(xavani v0.7)` — never fake a pass.
