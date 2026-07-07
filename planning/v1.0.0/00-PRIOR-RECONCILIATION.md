<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Phase-0 audit + close-out of the v0.7.0 Operator roadmap. -->

# Phase 0 — Prior-work reconciliation → release v0.9.0

The user asked to **finish the updates from previous sessions first**. Those updates are the two
local roadmaps: `planning/v0.4.0/ROADMAP.md` (v0.3.1→v0.6.0, 100 updates) and
`planning/v0.7.0/{ROADMAP,DESIGN}.md` (the Operator autonomy layer, 104 updates). This document
audits their state and defines exactly what remains before the four v1.0.0 majors begin.

## Audit snapshot (2026-06-11, branch `feat/xavani-v1-quantum-sentience`)

| Signal | Result |
|---|---|
| `git log` | v0.6.0 released (`5bc6841`); operator M0–M6 + M-Biz finance + design-craft all committed |
| `python3 -m pytest tests/operator -q` | **239 passed in 6.76s** |
| `xavani_operator/` modules present | `perceive, opportunities, decide, propose, approval_queue, act, verify, report, learn, loop, continuous, tiers, workflow, audit, notify, capability, scaffold, config, state, types` + `workstreams/` + `finance/` |
| Repo version string | still `0.6.0` in `pyproject.toml`, `xavani_cli/__init__.py`, `xavani.py` |

**Conclusion:** the v0.4.0 roadmap is shipped. The v0.7.0 Operator is built and green through
**M6** (durable DAG + continuous run) plus the M-Biz finance pack and the ML design-taste layer.
The remaining gap is **M7 (v0.9.0): teams, dashboard, hardening, release**.

## v0.7.0 roadmap status (per `planning/v0.7.0/ROADMAP.md`)

| Milestone | Theme | Status |
|---|---|---|
| M0 | Operator foundation | ✅ done |
| M1 | Perceive → Decide | ✅ done |
| M2 | Propose → Approve | ✅ done |
| M3 | Act → Verify → Report → Learn | ✅ done |
| ML | Learning & Taste layer | ✅ done (style_library + design-craft skill) |
| M4 | Build workstream | ✅ done (workstreams/build) |
| M5 | Promote workstream | ✅ done (workstreams/promote) |
| M6 | Durability (DAG) + continuous | ✅ done (`workflow.py`, `continuous.py`) |
| — | M-Biz finance (net-new, not in roadmap) | ✅ done (`finance/`) |
| **M7** | **Teams, dashboard, hardening, release** | **⛔ the gap** |

> Each row above must be re-verified at execution time with `pytest -k` + a smoke import, not
> taken on faith — the audit recorded a point-in-time snapshot.

## M7 close-out plan (→ v0.9.0)

Build in PR-sized steps; each = code + tests + Verify. The **dashboard (U93/U94) is intentionally
deferred to v1.0.0 major ④** so it is redesigned once, in the Enternovate system, with the new
quantum/oracle/advisor surfaces included.

1. **U91/U92 — Teams of operators.** Planner + specialist subagents (builder / marketer / verifier)
   over `tools/delegate_tool.py`, with file-ownership coordination (no two agents edit one file).
   New `xavani_operator/team.py`; tests with mocked delegate.
2. **U95 — Autonomy safety gate.** Before any outward content/action, run the `agent` injection/PII
   detectors on the proposal. Wire into `act.py` / `approval_queue.py`. Zero-LLM.
3. **U96 — Capability scoping (RBAC).** Per-workstream/persona action allow-list on the `act`
   dispatcher (extend `tools/registry.py` gate).
4. **U97 — Secrets isolation** for channel credentials (reuse `tools/credential_files.py`; never log).
5. **U98 — Red-team eval harness** for autonomous actions (exfil, rogue post, destructive op,
   injected goal). **Gates the release.**
6. **U99 — Kill-switch:** `xavani operator pause | kill | rollback` (global pause + emergency revert).
7. **U100 — Full E2E operator smoke** (build + promote, both dry-run) in CI.
8. **U101 — Operator tutorial + cookbook + STRIDE threat model** for autonomy.
9. **U102 — `xavani doctor` operator deep-check** + pydantic config validation messages.
10. **U104 — Version bump → 0.9.0** (R9) in `pyproject.toml` + `xavani_cli/__init__.py` + `xavani.py`;
    CHANGELOG; "1.0 readiness" note.

## Definition of done (Phase 0)

```
python3 -m pytest -q                          # full suite green, no new skips
python3 -m pytest -k "operator and no_llm"    # operator decision path makes ZERO model calls
python3 -m pytest -k "redteam or autonomy"    # U98 release-gating red-team evals pass
xavani doctor                                 # operator deep-check passes
xavani operator pause && xavani operator status   # kill-switch works
grep -niE 'version' pyproject.toml xavani.py xavani_cli/__init__.py   # all read 0.9.0
```

If any item can't be done safely, STOP and leave a precise `TODO(xavani v0.9)` with the blocker —
never fake a pass. Only the user pushes.
