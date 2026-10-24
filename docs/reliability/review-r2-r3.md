# R2/R3 review record — tasks 13, 17, 18

Date: 2026-09-14. Independent review in a fresh session, separate from the
task authors. Spec of record: `planning/reliability-master-plan.md`
(Code Packs K, M, N). Frozen revisions: desktop `f4d1086`; agent `3a1f208f`
(task 17), `41b95940` (task 18).

Method: per-microcycle DONE-vs-MISSING checklists mapped to executed
evidence; mutation probes on guarded production lines (probe → a test must
fail → revert byte-identical); defect reproduction against the pre-fix file;
live Electron evidence on an isolated home.

## Task 13 — workbench shell (desktop f4d1086) — CONFIRMED

| # | Microcycle | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Default layout has an editor and Agent pane | DONE | unit test; live regions |
| 2 | Workspace switch restores only that workspace's layout | DONE | 2 unit tests; wiring on root change |
| 3 | A saved layout clamps to the current viewport | DONE | unit; live no-scroll |
| 4 | Reset layout removes only layout preferences | DONE | unit (dock/follow/file pointer kept) |
| 5 | 980x620 retains every primary action | DONE (scope note F1) | live capture |
| 6 | 200% zoom has no page-level horizontal scroll | DONE | live capture |

Evidence (executed):

- `node --test tests/desktop/test_workbench_state.js` → 15 passed, 0 failed.
- Mutation probes (seq-guard, clamp, dirty-follow, flip-guard): each failed
  ≥1 committed test; every revert sha256-identical; worktree clean.
- `node --check` clean on `workbench-state.js` and `app.js`; script order
  (workbench-state.js before app.js) and CSS order verified in index.html.
- Live captures (isolated home): `desktop-task13-980x620-v2.png` (inner
  980x620, studio mode, all six regions correct, separators + reset-layout
  visible, tree rendered, 0 page errors) and `desktop-task13-zoom200-v2.png`
  (inner 660x430, compact grid `"activity editor"`, scrollWidth ≤ innerWidth,
  0 page errors). Storage: `~/xavani-backups-2026-09-14/`.

Finding F1 (recorded, not a task-13 blocker): in studio mode the chat
composer (`#send`) and the sidebar New chat (`#new-chat`) are hidden. The
desktop specification item "Keep chat visible during code work" (Agent pane)
is not implemented yet. Task 16's e2e should assert the shell controls in
studio mode and composer/New chat in chat mode — or the Agent-pane chat item
is scheduled as its own follow-up.

Residuals: `tests/e2e/workbench.spec.js` stays a skeleton until Task 16 owns
the harness (by design). Screenshots are held for owner approval before any
change to the old layout path (nothing removes it today; chat mode remains
reachable).

## Task 17 — workflow skills (agent 3a1f208f) — CONFIRMED, activation parked

Microcycles 1–10: all module-level DONE, each mapped to a named test (25
passed across `tests/agent/test_workflow_catalog.py` +
`test_workflow_skill_loading.py`).

Mutation probes: pruned-guard and boundary-changed each failed exactly 1
test; reverts clean.

Wiring decision (the flagged judgment call) — PARK with rationale:

- Wired in production now: receipt store attach (`agent_init.py`) and
  compression retention (`retain_workflow_receipts` in `compress_context`).
- No production call sites yet: `build_workflow_skill_message`,
  `record_selection`, `workflow_context_block`,
  `refresh_workflow_skills_at_boundary`, `ensure_workflow_skills_loaded`.
- Rationale: the plan's own rule — do not invent call sites before the
  owning task (same convention as the finance-validation wiring note). The
  workflow selector is Task 21's scope; the boundary and pre-action hooks
  land with the business layer. The module, receipts, and compression
  survival are complete and non-vacuously tested.
- Follow-up (tracked in SESSION_HANDOFF.md): at Task 21, wire
  `build_workflow_skill_message` + `record_selection` +
  `workflow_context_block` at the workflow selector;
  `refresh_workflow_skills_at_boundary` at the agent-loop task boundary;
  `ensure_workflow_skills_loaded` before consequential actions.

## Task 18 — finance validation (agent 41b95940) — CONFIRMED

Microcycles 1–10: all DONE (41 passed, including
`tests/operator/test_finance_ledger.py`).

Mutation probe: zero-denominator failed exactly 1 test; revert clean.

`money.py` defect fixes reproduced against the pre-fix file (`3a1f208f`):

- `test_money_rejects_bad_input_as_value_error` — FAIL pre-fix, PASS fixed.
- `test_vat_rate_must_be_finite_and_non_negative` — FAIL pre-fix, PASS fixed.

Defects proven: `decimal.InvalidOperation` / `OverflowError` leaked instead
of `ValueError`; NaN/Infinity accepted; negative VAT rate accepted.

Wiring: `validation.py` has no production callers yet — explicitly deferred
by the plan to the B01 source-adapter intake (Phase 3). No call sites were
invented.

## Integration state at review time

- PR #118: all test/security/build jobs pass (`test` 12m48s, ruff, bandit,
  semgrep, gitleaks, benchmarks, nix, builds). Non-green: CodeQL — 48 flagged
  alerts = the documented 45-alert clear-text-logging block (`# nosec` is
  Bandit-only; resolution is owner dismissals with `security_events` scope or
  the advanced-setup switch; the config file is already aligned) + 2
  test-file url-substring + 1 mitigated cookie-injection; and `test-windows`
  (re-run pending at review time). No branch protection: not a merge gate.
- Desktop repo: no CI workflows configured (known follow-up).

## Live-evidence hygiene (learned live; a Task 16 requirement)

Interim Electron evidence must run against an isolated `XAVANI_HOME` and
sweep the processes it creates. On quit, `serve_desktop` can orphan (PPID 1)
and an orphaned backend can keep executing an in-flight session turn. Treat
the Task 16 fixture requirements "isolated XAVANI_HOME" and "stop only the
processes that the fixture creates" as mandatory; consider a desktop
follow-up to reap the backend child on app quit.
