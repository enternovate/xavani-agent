<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Autonomy-layer roadmap (104 updates) for the implementing agent.
     Pairs with planning/v0.7.0/DESIGN.md. Keep untracked unless the user commits. USER controls pushes. -->

# Xavani Operator — v0.7.0 → v0.9.0 Roadmap (104 updates)

> **Goal:** turn Xavani into a self-initiating **full operator** that **builds + promotes** a
> plugged-in product end-to-end, deciding what to do and proposing it — the user just **approves**.
> **Bar:** each update is one small change + its tests + its Verify; do not start the next until the
> current is green. When unsure of an API, **READ the named file and mirror it — never guess.**
> **Spine (R10):** the LLM is for *generation only* (plans, code, copy). Perceive, opportunity
> detection, decide/rank, tier classification, and verify-gating are **pure Python, zero model calls.**
> House rules R1–R10 from `DESIGN.md §8` apply to every update. **The agent never pushes.**

Legend: **[MAJOR]** big/foundational · **[FEAT]** feature · **[SEC]** security · **[TEST]** · **[DOC]** · **[DX]** · **[PERF]** · **[CLI]**

---

## M0 — v0.7.0-α "Operator foundation"  (the plumbing every later update needs)

1. **[MAJOR]** Package skeleton → new `xavani_operator/__init__.py` + `types.py` (dataclasses:
   `Perception`, `Opportunity`, `Intent`, `Proposal`, `PlanStep`, `StepResult`, `Verdict`, `CycleReport`).
   Verify: `python3 -c "import xavani_operator"` OK; types import; R8 header on each file.
2. **[FEAT]** Config loader → `xavani_operator/config.py`: pydantic-v2 models for `xavani.product.yaml`
   (`product/goals/channels/brand/constraints/budgets/approval/schedule`) + `load_product_config(path)`.
   Read `xavani_cli/config.py` for yaml conventions; reuse `pyyaml`. Verify: valid file loads; bad file → clear error.
3. **[FEAT]** State store → `xavani_operator/state.py`: JSON/SQLite store under `~/.xavani/operator/`
   (cycles, proposals, task ledger). Reuse `agent/file_safety.py` home resolver. Verify: round-trip persistence test.
4. **[FEAT]** Tier classifier → `xavani_operator/tiers.py`: pure `classify(action_class) -> Tier{0..3}` +
   per-config overrides. Verify: table test maps each action-class to expected tier; zero I/O.
5. **[CLI]** `xavani operator init` → scaffolds a starter `xavani.product.yaml` with comments. Wire the
   `operator` subcommand group (read `xavani_cli/main.py`/`_parser.py` dispatch). Verify: init writes a valid file `config.py` accepts.
6. **[TEST]** Unit tests for config/state/tiers + a no-LLM assertion (monkeypatch model chokepoint to raise).
   Verify: `pytest tests/operator -q` green.
7. **[DOC]** `xavani_operator/README.md` + product.yaml field reference. R1 scrub.
8. **[DX]** Extend `xavani_cli/doctor.py`: operator section (config present? state writable? no model-client import in decision modules). Verify: `xavani doctor` passes.

## M1 — v0.7.0 "Perceive → Decide"  [MAJOR theme: the deterministic brain]

9. **[MAJOR][FEAT]** `perceive.py` git/repo signals (branch, dirty files, recent commits, work-branch state). Pure subprocess; no LLM.
10. **[FEAT]** perceive test/CI signals: parse `pytest`/CI status into `Perception.tests`. Read existing eval/test runners.
11. **[FEAT]** perceive TODO/FIXME/issue signals: scan tree + (optional) GitHub issues via existing github tooling.
12. **[FEAT]** perceive channel/inbox signals: unread/mentions across configured `gateway/platforms/*` (read-only).
13. **[FEAT]** perceive metrics + last-cycle signals: pull prior `CycleReport` + any analytics file.
14. **[FEAT]** `Perception` snapshot assembly + content-hash cache (reuse the content-hash cache pattern from the prior roadmap).
15. **[MAJOR]** `opportunities.py`: deterministic rule engine — `detect(perception) -> list[Opportunity]` with scores; stdlib only.
16. **[FEAT]** build opportunity rules (failing test→fix, stale docs→update, backlog item→build, debt hotspot→refactor).
17. **[FEAT]** promote opportunity rules (cadence due, release/milestone reached, notable commit → announce).
18. **[FEAT]** ops opportunity rules (outdated deps via `tools/osv_check.py`, security advisory, broken CI).
19. **[FEAT]** `decide.py`: rank opportunities under budgets/constraints/quiet-hours → top `Intent`. Deterministic tie-break.
20. **[FEAT]** `workstreams/base.py` `Workstream` protocol + registry; register build/promote/ops shells.
21. **[TEST]** perceive/opportunities/decide no-LLM harness (every function asserted to make zero model calls).
22. **[CLI]** `xavani operator perceive` (print snapshot) + `xavani operator decide --dry-run` (print ranked intents, no action).

## M2 — v0.7.1 "Propose → Approve"  [MAJOR: the human gate]

23. **[MAJOR][FEAT]** `propose.py`: `make_proposal(intent, ctx) -> Proposal` — **only place the LLM runs** in the loop; emits steps each tagged by tier.
24. **[FEAT]** `Proposal` artifact schema + persistence (state store); stable IDs; diff/draft attachments.
25. **[FEAT]** `approval_queue.py`: enqueue/list/get proposals; statuses (pending/approved/rejected/amended/expired).
26. **[MAJOR][FEAT]** Tiered approval gate: reuse `tools/approval.py`/`slash_confirm.py`; map tiers → prompts.
27. **[FEAT]** Plan-level approval semantics: approving a plan pre-authorizes its listed Tier-2 steps; **Tier-3 always reconfirms** at exec.
28. **[CLI]** `xavani operator proposals` (list/show with rendered plan + tiers).
29. **[CLI]** `xavani operator approve|reject|amend <id>` (amend = edit steps before approving).
30. **[FEAT]** Approval delivery via gateway: notify the user on their channel when a proposal needs them (reuse `send_message_tool`).
31. **[SEC]** Hash-chained, tamper-evident approval/decision audit log (extend any existing audit util).
32. **[FEAT]** Tier-1 veto window (auto-proceed after N minutes unless vetoed).
33. **[FEAT]** Budget guard at propose-time: skip/queue generation when over `budgets`.
34. **[TEST]** Approval-flow tests across the full tier matrix (0→3) incl. amend + veto.
35. **[TEST]** Cost test: only `propose.make_proposal` touches the model; everything else zero calls.
36. **[DOC]** Approval-model docs (tiers, overrides, plan-vs-action semantics).

## M3 — v0.7.2 "Act → Verify → Report → Learn"  [MAJOR: closes the cycle]

37. **[MAJOR][FEAT]** `act.py`: execute an approved `Proposal` — dispatch each `PlanStep` to the right tool/subagent.
38. **[FEAT]** Work-branch isolation: each cycle runs in a git worktree/branch (reuse `using-git-worktrees` pattern); never on `main`.
39. **[FEAT]** Tier-gated per-action execution inside `act` (Tier-3 reconfirm; Tier-2 honored if pre-authorized).
40. **[FEAT]** `verify.py`: run tests/lint/smoke; build a `Verdict`. Deterministic.
41. **[FEAT]** verify content/brand policy checks for promote steps (deterministic rules + optional critique).
42. **[FEAT]** Rollback on verify failure: revert the work branch; mark cycle failed with reason.
43. **[FEAT]** `report.py`: build a `CycleReport` (proposed/approved/done/verified/learned + cost).
44. **[FEAT]** Deliver the report via CLI + gateway.
45. **[FEAT]** `learn.py`: write outcomes to `xavani_memory/` + `agent/insights.py`.
46. **[FEAT]** learn: update opportunity weights deterministically from outcomes (success→up, fail→down).
47. **[MAJOR][FEAT]** `loop.py`: single-cycle orchestrator wiring Perceive→Opportunities→Decide→Propose→[gate]→Act→Verify→Report→Learn.
48. **[FEAT]** Checkpoint/resume the loop (reuse `tools/checkpoint_manager.py`); resume mid-cycle after interrupt.
49. **[TEST]** End-to-end single-cycle test with a mock workstream + stubbed propose (no real LLM): asserts the full loop + gate.
50. **[CLI]** `xavani operator cycle` (run one cycle to the gate) + `xavani operator status` (current state, open proposals).

## ML — v0.8.0-pre "Learning & Taste layer"  [MAJOR]  (runs after M3; feeds M4/M5)

> **Why:** the agent should learn the user — design taste, preferences, how they
> organise — *once*, then default to it. Profiles set creative **direction** (high
> craft, distinctive); they never replace the agent's creativity, and a guardrail
> keeps output **away from generic/template-y, easily-identifiable** designs.
> **Spine (R10):** learn once (LLM distils a profile), then **select + apply
> deterministically**. Extends the existing `xavani_learner/user_profile.py`.

L1. **[MAJOR]** `xavani_learner/style_profile.py` — `StyleProfile` schema (name, inspiration[attributed],
    tags, layout, typography, color, motion, whitespace/density, imagery, feel[], avoid[]) + library loader.
L2. **[FEAT]** Seed curated library `xavani_learner/style_library/*.yaml` — profiles distilled from the
    user's references (clarity/precision, immersive-motion, fintech-density, playful-brand, editorial,
    type-specimen, data-clean, brutalist-experimental…) + the principle categories the eleken blog teaches.
    Each profile is **inspiration-attributed**, never a copy; no verbatim assets (L12).
L3. **[FEAT]** Deterministic style selector — `select_style(brief, profiles) -> ranked` by keyword/tag
    overlap (mirror `skill_router`); picks the best-matching direction for the brief. Zero LLM (R10).
L4. **[MAJOR][FEAT]** Anti-generic guardrail — `flag_generic(design) -> findings`: deterministic checks that
    flag template-y choices (default framework looks, generic hero+3-cards, stock spacing/type) and nudge
    toward distinctive craft. Register in `agent/detectors.py`.
L5. **[FEAT]** `xavani learn <url>` intake — fetch + distil a `StyleProfile` (LLM extract = the allowed
    generation), store **once**; thereafter reused deterministically.
L6. **[FEAT]** `xavani learn <file>` and `xavani learn "I prefer X"` intake (design refs + stated prefs).
L7. **[FEAT]** Extend `user_profile.py` to capture design references + preferences continuously (passive).
L8. **[FEAT]** Taste/preference recall → inject the selected profile + prefs into the generation context.
L9. **[FEAT]** Wire selector+profile+guardrail into the build workstream's website generation (with M4).
L10. **[CLI]** `xavani learn list|show` — inspect learned profiles + preferences.
L11. **[TEST]** Selector determinism, guardrail, profile round-trip — all asserted **zero-LLM**.
L12. **[SEC][DOC]** Copyright-safety: every profile attributes inspiration, stores no verbatim assets/markup;
     output is original work in the learned direction.
L13. **[DOC]** Learning-layer guide: how taste is learned, selected, and applied; how to teach it more.
L14. **[TEST]** Continuous-capture tests (refs/prefs learned from conversation feed recall).

## M4 — v0.8.0 "Build workstream (full-stack)"  [MAJOR]  (consumes ML for website design)

51. **[MAJOR][FEAT]** `workstreams/build.py` opportunity detection (features from goals, bugs from failing tests, debt hotspots).
52. **[FEAT]** build: feature-spec generation (LLM) → structured plan; integrate `xavani_cli/kanban_specify.py`/`decompose.py`.
53. **[FEAT]** build: backend implementation step via `tools/delegate_tool.py` subagents (file-scoped).
54. **[FEAT]** build: frontend implementation step (web/ or configured frontend).
55. **[FEAT]** build: infra/migrations step (db migration, IaC) behind tier-2.
56. **[FEAT]** build: test-first gate — generate tests, require green before proceeding (TDD).
57. **[FEAT]** build: integrate goals ledger (`xavani_cli/goals.py`) so goals drive/track features.
58. **[FEAT]** build: draft-PR creation (Tier-1) via github tooling; never auto-merge.
59. **[FEAT]** build: deploy step (Tier-2) with pluggable adapters (vercel/docker/ssh from `tools/environments/*`).
60. **[FEAT]** build: changelog/release-notes generation from the cycle's commits.
61. **[SEC]** build: run code-review + security scan (`tools/osv_check.py`, existing security CI) as a gate before PR.
62. **[TEST]** build-pack tests with mocked subagents + git (no network).
63. **[PERF]** build: parallelize independent steps (bounded concurrency via delegate).
64. **[DOC]** build-workstream guide (how goals → features → PR → deploy).

## M5 — v0.8.1 "Promote workstream (growth)"  [MAJOR]

65. **[MAJOR][FEAT]** `workstreams/promote.py` opportunity detection (cadence due, release reached, milestone/event, notable change).
66. **[FEAT]** promote: per-channel content generation (LLM) honoring `brand.voice`/dos/donts.
67. **[FEAT]** promote: media generation via `image_generation_tool`/`video_generation_tool` (optional, budgeted).
68. **[FEAT]** promote: channel adapters (X, Discord, Telegram, email, blog) over `gateway/platforms/*` + `send_message_tool`.
69. **[FEAT]** promote: scheduling/calendar via `cronjob_tools.py` + quiet hours.
70. **[SEC]** promote: brand/policy/safety check before **any** outward post (deterministic rules + optional critique); blocks on fail.
71. **[FEAT]** promote: posting as **Tier-2** with a rendered preview in the proposal.
72. **[FEAT]** promote: landing/changelog/blog publishing (static file or configured CMS).
73. **[FEAT]** promote: analytics ingestion — engagement metrics flow back into `perceive`.
74. **[FEAT]** promote: A/B variant generation + **deterministic** selection rule (no LLM to pick).
75. **[FEAT]** promote: audience/lead tracking ledger.
76. **[TEST]** promote-pack tests with dry-run channels (no real posts).
77. **[SEC]** promote: per-channel rate limit + spend guard (generalize existing platform rate limiting).
78. **[DOC]** promote-workstream guide (channels, cadence, brand, safety).

## M6 — v0.8.2 "Durability (DAG) + continuous operation"  [MAJOR]

79. **[MAJOR][FEAT]** Durable workflow/DAG engine → `xavani_operator/workflow.py` (steps, deps, retries, resume, idempotency keys).
80. **[FEAT]** Model cycles as durable workflows (act/verify steps become DAG nodes).
81. **[FEAT]** Continuous `xavani operator run`: cadence loop from `schedule.cycle_cadence`, budget/iteration-governed.
82. **[FEAT]** Watchers → triggers: file/repo/issue/metric watchers spawn cycles (reuse cron + watcher pattern).
83. **[FEAT]** Quiet-hours + budget-aware scheduling (defer outward actions; throttle generation).
84. **[FEAT]** Crash recovery + idempotent steps (resume exactly-once; no duplicate posts/PRs).
85. **[FEAT]** Concurrency control: one active cycle per repo; queue the rest.
86. **[SEC]** Durable, tamper-evident run log of every action (extends U31 audit).
87. **[FEAT]** Backpressure: pause new cycles when pending approvals exceed a threshold.
88. **[TEST]** Durability tests: kill mid-cycle, resume, assert no duplicate side effects.
89. **[PERF]** Loop startup + perceive caching budget (sub-second perceive on warm cache).
90. **[DOC]** Continuous-operation guide (run as a service, watchers, quiet hours).

## M7 — v0.9.0 "Teams, dashboard, hardening, release"  [MAJOR]

91. **[MAJOR][FEAT]** Multi-agent team-of-operators: planner + specialist subagents (builder/marketer/verifier) over the delegate bus.
92. **[FEAT]** File-ownership coordination for parallel agents (no two agents edit the same file).
93. **[FEAT]** Web dashboard (`web/`): live operator monitor + proposal approve/reject UI.
94. **[FEAT]** Dashboard: run history + cost/savings analytics (R10 avoided-cost surfaced).
95. **[MAJOR][SEC]** Autonomy safety: prompt-injection-aware proposal gating (reuse `agent/detectors.py` injection/PII) before any external content/action.
96. **[SEC]** Capability scoping per workstream/persona — RBAC on the `act` dispatcher (extend `tools/registry.py` gate).
97. **[SEC]** Secrets isolation for channel credentials (reuse `tools/credential_files.py`; never log/embed).
98. **[MAJOR][SEC]** Red-team eval harness for autonomous actions (exfil, rogue post, destructive op, injected goal) — **gates releases**.
99. **[FEAT]** Kill-switch + global pause + emergency rollback (`xavani operator pause|kill|rollback`).
100. **[TEST]** Full E2E operator smoke (build + promote, both dry-run) in CI.
101. **[DOC]** Operator tutorial + cookbook + STRIDE threat model for autonomy.
102. **[DX]** `xavani doctor` operator deep-check + pydantic config validation messages.
103. **[PERF]** Cost dashboard + avoided-cost (R10) savings report (`xavani operator status --savings`).
104. **[MAJOR]** v0.9.0 release: version bump (R9), CHANGELOG, "1.0 readiness" review + roadmap refresh.

---

## Tally
- **[MAJOR]** = U1, U9, U15, U23, U26, U37, U47, U51, U65, U79, U91, U95, U98, U104 → **14** (≥12 ✓)
- **[FEAT]** ≥ 50 ✓ · **[SEC]** = U31, U61, U70, U77, U86, U95, U96, U97, U98 (+cross-cutting) ✓
- **[TEST]/[DOC]/[DX]/[PERF]/[CLI]** present in every milestone ✓

## Sequencing
**M0 → M1 → M2 → M3 (loop closes; releasable) → M4 ∥ M5 (build & promote packs) → M6 (durable/continuous) → M7 (teams/hardening/release).**
Each update = one PR-sized change + tests + Verify. Bump the version (R9) once per milestone tag.
Milestones M0–M3 already deliver a working, approve-gated operator (with a mock/simple workstream);
M4+ make it genuinely full-stack build + promote.

## Definition of Done — see `DESIGN.md §9`.
If an item can't be done safely, STOP and leave a precise `TODO(xavani v0.7)` with the blocker — never fake a pass.
