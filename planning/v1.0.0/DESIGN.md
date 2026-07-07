<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Architecture + module map for the v1.0.0 majors. -->

# v1.0.0 — Architecture & Design

## 1. House rules (carried from `planning/v0.7.0/DESIGN.md §8` — non-negotiable)

- **R1 Scrub** — no new `nous`/`hermes` in shipped artifacts (only existing LICENSE/README
  attribution). `@nous-research/ui` is an upstream npm library and may stay as a dependency, but all
  **visible UI chrome/labels become Enternovate**.
- **R2 Stubs** — never touch `tools/skills_hub.py` / `gateway/platforms/weixin.py` bodies or test skips.
- **R3 Xavani-native** — re-implement; never copy upstream code/names.
- **R4 Surgical diffs. R5 Tests for every change; `pytest -q` green; no new skips.**
- **R7 Identity** — never rewrite `xavani_cli/default_soul.py` / `agent/prompt_builder.py`; the
  conscience/soul layer **appends** through `xavani_cli/research_guidelines.py` only.
- **R8** — Enternovate copyright header on every new `.py`. **R9** — version bump once per milestone.
- **R10 Deterministic-first (the spine)** — the LLM **generates only** (proposals, advice copy,
  distilling public playbooks). Decision, ranking, quantum collapse, downfall detection, model
  routing, consequence scoring, and scheduling are **pure Python, zero model calls**, each unit-tested
  to make zero model-client calls (mirror `tests/agent/test_detectors_no_llm.py`).
- **The agent never pushes / never commits.** Interpreter is `python3`.

## 2. Module map (new + touched)

| Area | New | Touched (append/extend only) |
|---|---|---|
| ① Quantum | `xavani_operator/quantum/{__init__,state,simulate,interference,collapse,qubo,outcome_patterns}.py` + `quantum/backends/{__init__,inspired,qiskit_aer,ibm_quantum,braket,dwave}.py` | `xavani_operator/decide.py`, `learn.py`, `cli.py`, `config.py`, `pyproject.toml` (optional `quantum` extra) |
| ② Oracle | `xavani_wisdom/{__init__,patterns,consequence,advisor_lens,self_faults,research}.py` + `xavani_wisdom/detectors/downfall.py` + `xavani_wisdom/corpus/{ascent,downfall}/*.yaml` + `skills/research-guidelines/conscience.md` | `agent` detector registry, `xavani_cli/research_guidelines.py` (register the conscience pack) |
| ③ Companion | `model_router.py` + `model_capabilities.yaml`; `xavani_operator/daemon.py`; `xavani_operator/advisor/{__init__,daily_brief,error_log,tomorrow_plan,reminders}.py`; `packaging/launchd/com.enternovate.xavani.plist`, `packaging/systemd/xavani-operator.service` | `xavani_operator/{continuous,cli}.py`, `cron/jobs.py`, `run_agent.py` (router hookup), `xavani_operator/propose.py` |
| ④ Dashboard | `web/src/themes/enternovate.*`; new page components under `web/src/pages/` (Quantum, Oracle, DailyCounsel, Operator, ModelRouter, Cost) | `web/src/index.css`, `web/src/App.tsx`, `web/src/components/ThemeSwitcher.tsx`, `xavani_cli/web_server.py` (read-only JSON endpoints) |

## 3. Data flow (deterministic spine)

```
decide.py  ──►  quantum.state.Superposition(branches)
                     │  (each Branch = an Opportunity/strategy)
                     ▼
            quantum.simulate.rollout(branch)  ──uses──►  wisdom.consequence.project(branch)
                     ▼                                        │
            quantum.interference.matrix(branches) ◄───────────┘ (downfall signatures lower amplitude)
                     ▼
            quantum.collapse.measure(ψ)  ──►  chosen Intent  ──►  propose.py
                     ▼
            quantum.outcome_patterns.record(branches, realized)  ──►  learn.py (weights)
                     ▼
            wisdom.self_faults.update(error_log, outcomes)  ──►  downfall detector (personalised)
```

The **only** LLM calls in this whole flow are inside `propose.make_plan`, `advisor.daily_brief`
(advice copy), and `wisdom.research` (distilling public playbooks). Everything else is pure Python.

## 4. Reuse map (build on primitives, don't reinvent)

| Need | Existing module |
|---|---|
| Decision / loop / continuous | `xavani_operator/{decide,loop,continuous,learn,tiers,state,report,notify,approval_queue,workflow}.py` |
| Scheduling / cron | `cron/scheduler.py`, `cron/jobs.py` |
| Checkpoint / resume | `tools/checkpoint_manager.py` |
| Model metadata / provider auto-detect | `agent/model_metadata.py`, `agent/models_dev.py`, `providers/__init__.py`, `providers/base.py` |
| Deterministic detection registry | the `agent` detectors (mirror `tests/agent/test_detectors_no_llm.py`) |
| Memory / insights / learning | `xavani_memory/`, `agent/insights.py`, `agent/curator.py`, `agent/background_review.py` |
| Design taste | `xavani_learner/style_library/*.yaml`, `skills/design/SKILL.md`, `xavani_learner/design_review.py` |
| Soul (append-only) | `xavani_cli/default_soul.py`, `xavani_cli/research_guidelines.py` |
| Messaging / Telegram | `tools/send_message_tool*`, `gateway/platforms/telegram*` |
| Budget / cost | `agent/budget_governor.py`, `account_usage.py` |
| Approval / HITL | `tools/approval.py`, `slash_confirm.py`, `interrupt.py`, `xavani_operator/tiers.py` |

## 5. Optional dependencies (extras, lazy-imported, credential-gated)

```toml
[project.optional-dependencies]
quantum = ["qiskit", "qiskit-aer", "qiskit-ibm-runtime", "amazon-braket-sdk", "dwave-ocean-sdk", "numpy"]
```

`select_backend()` mirrors the model-provider auto-detect: it picks a real QPU backend **only** when
its SDK *and* credentials are present (`IBM_QUANTUM_TOKEN`, `AWS_*` + Braket, `DWAVE_API_TOKEN`),
otherwise falls back to the always-on pure-Python `inspired` backend. No heavy dep is ever forced.

## 6. Test strategy

- **Determinism:** every decision/score function is called twice with the same seed → identical output.
- **Zero-LLM:** a fixture monkeypatches the model-client chokepoint to raise; the whole decision flow
  (quantum + oracle + router) runs without tripping it.
- **Fallback:** with no quantum creds, `select_backend()` returns `inspired`; with a fake creds env,
  it returns the right backend name (import guarded so CI without the SDK still passes).
- **Round-trip:** corpus YAML, outcome patterns, error-log entries persist and reload unchanged.
- **Identity:** composing the soul with the conscience pack leaves the base identity block byte-identical.
