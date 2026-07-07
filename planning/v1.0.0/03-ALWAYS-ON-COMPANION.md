<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Spec for major ③ — the Always-On Companion. -->

# ③ The Always-On Companion — 24/7 daemon + model router + advisor rituals

## Purpose

Make Xavani a 24/7 personal advisor that is **active only when actually working and generating
results**, routes each task to the **best available model**, sends a **daily brief**, runs the **8pm
error-log ritual**, captures **tomorrow's plan**, and **chases tasks hourly** — all over **Telegram**.
Deterministic where it decides; the LLM only writes the advice copy.

## Part A — Intelligent model router (`model_router.py` + `model_capabilities.yaml`)

```python
def route(task_class: str, *, available: set[str] | None = None) -> str:
    """Return the best AVAILABLE model id for a task class. Deterministic, zero API calls."""
```

- **Task classes:** `judgment` (emails, decisions, advice — "best knowledgeable critical thinker with
  proper reasoning"), `code`, `quick` (classify/route/extract — cheap+fast), `vision`, `long_context`,
  `bulk`. Extensible via the YAML.
- **Availability** = which provider API keys are present *right now* — reuse the existing provider
  auto-detect (`providers/__init__.py`, `agent/model_metadata.py`). The user adds/updates keys freely;
  the router re-resolves on every call, so new providers light up automatically.
- **Capability map** (`model_capabilities.yaml`, data-driven, user-editable): each known model →
  `{provider, reasoning_tier (1–5), strengths: [...], context, cost_tier}`. The router picks the
  highest-scoring model for the task class among the available providers; unknown models get sane
  defaults so nothing breaks when the user adds a brand-new model.
- **Wiring:** `run_agent.py` and `xavani_operator/propose.py` ask the router for the model per task;
  CLI `xavani model route <task_class>` prints the resolved model + why. **Zero model calls (R10).**

## Part B — 24/7 daemon (`xavani_operator/daemon.py`)

Wraps the existing `continuous.py` (which already has quiet-hours, concurrency lock, backpressure) as
a managed service:
- `xavani operator serve [--dry-run]` — run the continuous loop with a **heartbeat** file, a small
  **health** endpoint, and **crash-recovery** (resume via `tools/checkpoint_manager.py` + the M6 DAG).
- **"Active only when working":** a tick that finds no real opportunity does nothing but a cheap
  heartbeat (no LLM); a tick with a real opportunity runs a full cycle and **emits a result**
  (proposal/PR/post/report). Liveness = results produced, surfaced on the dashboard (④).
- **Service units:** `packaging/launchd/com.enternovate.xavani.plist` (macOS),
  `packaging/systemd/xavani-operator.service` (Linux), plus a documented Docker path.
- `xavani operator pause | kill` (shared with Phase-0 U99 kill-switch).

## Part C — Advisor rituals (`xavani_operator/advisor/`)

All scheduled through `cron/` and delivered via Telegram (`tools/send_message_tool` + the telegram
gateway adapter). Outward messages are **Tier-2** (go through `tiers.py` + `tools/approval.py`).

- **`daily_brief.py`** — morning brief: the day's perceptions + open goals + the Oracle's wisdom
  verdict + the Quantum decision, written as thoughts/advice/recommendations (LLM = copy only).
- **`error_log.py`** — **the 8pm ritual.** Asks exactly: *What did you predict that didn't happen?
  What did you believe yesterday that turned out off? Where did you waste effort because an assumption
  was wrong?* Stores a **structured error-log entry** (not a feelings journal) in `xavani_memory/`.
  Feeds `xavani_wisdom/self_faults.py`.
- **`tomorrow_plan.py`** — same 8pm session captures tomorrow's plan/tasks into the goals/kanban
  ledger (`xavani_cli/goals.py` / `tools/kanban_tools.py`).
- **`reminders.py`** — **hourly task-chase** (during waking hours): checks the day's open tasks and
  nudges via Telegram until done; inbound Telegram replies mark tasks done + update memory.
- **"Ask people about their day"** — the same ritual engine, pointed at a configurable contact list,
  Tier-2-gated because it is outward messaging.

### Error-log entry schema (stored in `xavani_memory/`)

```yaml
date: 2026-06-11
predictions_missed: [{predicted, actual}]
beliefs_revised:     [{believed, corrected}]
wasted_effort:       [{assumption, cost}]
tomorrow_plan:       [{task, why, est}]
```

## Schedule (registered in `cron/jobs.py`)

| Job | Cron | Action |
|---|---|---|
| `xavani.advisor.morning_brief` | `0 8 * * *` | send the daily brief |
| `xavani.advisor.hourly_chase` | `0 9-21 * * *` | nudge open tasks |
| `xavani.advisor.evening` | `0 20 * * *` | 8pm error log + tomorrow's plan |

## Tests

- `test_router_deterministic` + `test_router_availability` — same inputs → same model; keys present/
  absent flips the choice; unknown model → default; **zero API calls**.
- `test_daemon_heartbeat` — serve loop writes a heartbeat, honours quiet-hours, resumes after a faked crash.
- `test_error_log_roundtrip` — ritual entry persists + reloads; feeds self_faults.
- `test_schedule_registration` — the three cron jobs register with the right specs.
- `test_telegram_dry_run` — brief/reminder render + "send" in dry-run without a real network call.

## Definition of done

`xavani model route email` returns the best available reasoning model with no API call ·
`xavani operator serve --dry-run` heartbeats + honours quiet-hours · the three cron jobs scheduled ·
8pm entry stored + visible on the dashboard · all delivery Tier-2-gated · R8 headers · R10 clean.
