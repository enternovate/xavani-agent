<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Numbered updates + sequencing for v1.0.0. Pairs with DESIGN.md. -->

# Xavani v1.0.0 — Roadmap (numbered updates)

Legend: **[MAJOR]** foundational · **[FEAT]** · **[SEC]** · **[TEST]** · **[DOC]** · **[CLI]** · **[DX]**
Each update = one PR-sized change + its tests + its Verify. Do not start the next until the current is
green. When unsure of an API, **READ the named file and mirror it — never guess.** R1–R10 apply
(see `DESIGN.md §1`). **The agent never pushes.**

## Phase 0 — finish the Operator → v0.9.0  (detail in `00-PRIOR-RECONCILIATION.md`)
P1 [MAJOR] teams-of-operators (`xavani_operator/team.py`, U91/U92) · P2 [SEC] autonomy safety gate
(U95) · P3 [SEC] capability RBAC (U96) · P4 [SEC] secrets isolation (U97) · P5 [SEC][TEST] red-team
eval harness, release-gating (U98) · P6 [FEAT][CLI] kill-switch `pause|kill|rollback` (U99) ·
P7 [TEST] E2E operator smoke (U100) · P8 [DOC] operator tutorial + STRIDE (U101) · P9 [DX] doctor
deep-check (U102) · P10 [DX] **version → 0.9.0** + CHANGELOG (U104).

## ② Oracle (build first of the majors)  → `xavani_wisdom/`
1. [MAJOR] package skeleton + `patterns.py` (schemas + YAML loader + deterministic `match`).
2. [FEAT] seed corpus `corpus/{ascent,downfall}/*.yaml` (~15–20 attributed entries).
3. [MAJOR] `consequence.py` — deterministic 2nd/3rd-order projection → `ConsequenceReport`.
4. [SEC] `detectors/downfall.py` + register in the `agent` detector registry (zero-LLM).
5. [FEAT] `self_faults.py` — own-fault → personalised downfall signatures.
6. [FEAT] `advisor_lens.py` — fuse into a `WisdomVerdict`.
7. [FEAT] `research.py` — study public playbooks (LLM distil = the only generation).
8. [DOC] soul: `skills/research-guidelines/conscience.md` + `wisdom.md`; register in `research_guidelines.py` (append-only).
9. [TEST] corpus-loads · downfall-no-LLM · consequence-deterministic · self-faults-learn · soul-append-safe.
10. [CLI] `xavani wisdom verdict <ctx>` / `xavani wisdom corpus`.

## ① Quantum Decision Cortex  → `xavani_operator/quantum/`
11. [MAJOR] `state.py` — `Branch` / `Superposition` + `superpose()`.
12. [MAJOR] `simulate.py` — seeded Monte-Carlo rollouts consuming `wisdom.consequence`.
13. [FEAT] `interference.py` — pairwise risk-correlation matrix.
14. [MAJOR] `collapse.py` — deterministic Born-rule measurement → `Decision`.
15. [FEAT] `qubo.py` + `backends/inspired.py` (simulated annealing, always-on).
16. [FEAT] `backends/{qiskit_aer,ibm_quantum,braket,dwave}.py` + `select_backend()` (lazy, cred-gated).
17. [FEAT] `outcome_patterns.py` — record + `compare()` → weight deltas for `learn.py`.
18. [FEAT] wire into `decide.py` behind `config.quantum.enabled`; feed `learn.py`.
19. [TEST] collapse-deterministic · no-LLM · backend-fallback · qubo-small · outcome-roundtrip.
20. [CLI] `xavani operator quantum [--last|--explain]`.

## ③ Always-On Companion  → `model_router.py` + `xavani_operator/{daemon,advisor}/`
21. [MAJOR] `model_router.py` + `model_capabilities.yaml`; reuse provider auto-detect; `route()` (zero API).
22. [CLI] `xavani model route <task_class>` (+ `--why`).
23. [FEAT] wire router into `run_agent.py` + `xavani_operator/propose.py`.
24. [MAJOR] `xavani_operator/daemon.py` — heartbeat + health + crash-recovery over `continuous.py`.
25. [FEAT][CLI] `xavani operator serve [--dry-run]`; service units (launchd/systemd/docker).
26. [FEAT] `advisor/daily_brief.py` (LLM = copy only) → Telegram (Tier-2).
27. [MAJOR] `advisor/error_log.py` — the **8pm ritual** + structured store in `xavani_memory/`.
28. [FEAT] `advisor/tomorrow_plan.py` → goals/kanban ledger.
29. [FEAT] `advisor/reminders.py` — hourly task-chase + inbound-reply handling.
30. [FEAT] register cron jobs (`morning_brief` 08:00, `hourly_chase` 09–21, `evening` 20:00).
31. [FEAT] "ask people about their day" check-in (configurable contacts, Tier-2).
32. [TEST] router-deterministic/availability · daemon-heartbeat · error-log-roundtrip · schedule · telegram-dry-run.

## ④ Mission Control dashboard  → `web/` + `xavani_cli/web_server.py`
33. [DOC] audit notes (routes, endpoints, broken/placeholder, missing copy) → append to `04-...md`.
34. [FEAT] complete all UI copy + i18n; fix broken pages; WCAG-AA baseline.
35. [SEC] scrub visible "Nous" branding from UI chrome (R1).
36. [MAJOR] `web/src/themes/enternovate.*` + make default; rebuild `index.css` LENS defaults to navy.
37. [FEAT] typography + motion pass (dark-elegance profile + `design` skill).
38. [FEAT] read-only endpoints in `web_server.py` (quantum/wisdom/advisor/operator/router/cost).
39. [MAJOR] pages: Quantum Decision · Oracle · Daily Counsel · Operator/24-7 (approve queue = M7 U93/U94).
40. [FEAT] pages: Model Router · Cost & Savings.
41. [TEST] `npm run build` green; playwright nav + screenshots + contrast check.
42. [DX] **version → 1.0.0** + CHANGELOG + README dashboard section.

## Sequencing
**Phase 0 → ② → ① → ③ → ④.** ② ships a usable conscience + detector; ① consumes ②; ③ consumes ①+②;
④ surfaces everything. Each milestone is independently releasable.

## Definition of done — see `OVERVIEW.md`. Per-major DoD lives in each `0N-*.md`.
If an item can't be done safely, STOP and leave `TODO(xavani v1.0)` with the blocker — never fake a pass.
