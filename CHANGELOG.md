# Changelog

All notable changes to Xavani Agent are documented in this file.

## [0.7.2] - 2026-08-01 — "Deploy Readiness"

Deploy hardening. No new user-facing features.

### Added
- New blocking `core-gate` CI job: smoke-imports all core subsystems and runs
  the stable approval + MOA unit tests. Any failure blocks the merge. The full
  suite stays non-blocking (visibility) to avoid blocking on known real-time
  flakes. Implements the "no test stays red >1 release" failure budget (A05).
- `--dist=loadscope` was evaluated for the full suite and **rejected**: measured
  ~4x wall-clock regression (38% at 10 min) because the large `xavani_cli`
  module pins to one worker, risking the CI 30-min timeout. Flake prevention
  stays at the test level (deadline-based waits) to keep the fast path.
- New shared `wait_for_state(predicate, timeout, interval)` pytest fixture
  (tests/conftest.py) — the canonical deadline-based poller that replaces
  fixed-sleep / fixed-iteration-cap waits (A01). Applied to the 4 timing-fragile
  gateway approval poll loops; covered by its own unit test.

## [0.7.0] - 2026-06-12 — "Quantum Sentience"


Four major updates, each deterministic and zero-LLM at its core: the LLM only
*generates* (plans, advice copy), never routes or decides.

### Added

#### ① Quantum Decision Cortex (`xavani_operator/quantum/`)
- Decisions made by holding candidate strategies in **superposition**, simulating their
  outcomes, letting correlated risks **interfere**, then **collapsing** (Born-rule) to the
  best move — so the operator steers away from high-score-but-fragile options.
- `qubo.py` + pluggable `backends/` — classical `inspired` solver always on; optional real
  QPU (Qiskit / IBM / Braket / D-Wave) auto-selected only when credentials are present.
- `outcome_patterns.py` records each decision + its realised result and compares them.
- Wired into `xavani_operator/decide.py` behind `config.quantum.enabled` (default off).
- CLI: `xavani operator quantum`.

#### ② The Oracle — consequence-conscious wisdom (`xavani_wisdom/`)
- A corpus of how the great **rose and fell** (Solomon, Bezos, Buffett; Kodak, Lehman,
  Enron, WeWork, Icarus), a deterministic **consequence projector**, and a **downfall
  detector** registered in `agent.detectors`.
- `self_faults.py` turns the user's own recurring mistakes (from the 8pm log) into
  personalised watch-patterns.
- **Conscience soul pack** (`skills/research-guidelines/conscience-guidelines.md`) now rides
  in every session (append-only; base identity untouched, R7).
- CLI: `xavani wisdom verdict` / `xavani wisdom corpus`.

#### ③ The Always-On Companion
- **Intelligent model router** (`model_router.py` + `model_capabilities.yaml`): best
  available model per task by the API keys you've set (best critical-thinker for emails,
  cheap+fast for bulk). Zero API calls to decide. CLI: `xavani model --route <task>`.
- **24/7 daemon** (`xavani_operator/daemon.py`): heartbeat, "active only when working,"
  crash-safe. `xavani operator serve`; launchd + systemd units under `packaging/`.
- **Kill-switch** (`xavani_operator/killswitch.py`): `xavani operator pause` / `resume`.
- **Advisor rituals** (`xavani_operator/advisor/`): morning brief, the **8pm error-log**
  ritual, tomorrow-plan capture, and **hourly task-chase** — delivered over Telegram
  (08:00 / 09–21 / 20:00 cron specs).

#### ④ Mission Control dashboard (`web/`)
- Rebranded to the **Enternovate deep-navy** theme (electric-blue accent), default; the
  original look preserved as the `teal` theme.
- New **Sentience** page (quantum waveform + interactive Oracle consequence-check + model
  router) and **Daily Counsel** page (24/7 health + the 8pm error-log timeline), with
  read-only API endpoints under `/api/quantum`, `/api/wisdom`, `/api/router`,
  `/api/operator`, `/api/advisor`.

### Notes
- Optional quantum + Telegram dependencies are extras, lazy-imported, credential-gated.
- **Deferred to a follow-up (post-1.0 operator hardening):** multi-operator teams and a
  formal red-team eval harness for autonomous actions. Current safety rests on tiered
  approval, the kill-switch, and the downfall detector.

## [0.6.0] - 2026-06-02

### Added

#### Zero-cost cognition (deterministic, no-LLM detection)
- `tools/tool_prefilter.py` — deterministic per-turn tool pre-filter; selects the relevant tool subset from the user's message via keyword/intent rules, shrinking the function-call schema and cutting input-token cost. Never hides a needed tool (falls back to the full set; essentials always included).
- `agent/detectors.py` — pure-Python detector registry (scrub, stub-guard, secret-leak) with a uniform `Verdict` interface.
- `skills/research-guidelines/DETERMINISM-RULE.md` — the R10 "deterministic-first" rule (LLM is for generation only; never for routing/detection/governance).
- Enforcement: `tests/agent/test_deterministic_no_llm.py` fails CI if any detection/routing module imports a model client.

#### New tools
- `read_document` (`tools/document_tools.py`) — extract text from `.txt`/`.md`/`.csv`/`.json` natively and `.pdf`/`.docx`/`.xlsx`/`.pptx` via optional parsers (graceful missing-dep messages).
- `tools/mcp_server.py` — expose the tool registry over the Model Context Protocol; schemas reused verbatim, calls dispatch through the agent's own path.

#### Full-stack security
- `tools/egress_policy.py` — network egress allowlist with optional default-deny, configured via `XAVANI_EGRESS_ALLOWLIST` / `XAVANI_EGRESS_DEFAULT_DENY`.
- `tools/sandbox_hardening.py` — OS resource caps (address space / CPU time / open files, never raised above the hard cap) plus Linux-gated seccomp/Landlock status detection.
- `.github/workflows/security.yml` — Bandit, Gitleaks, Semgrep, pip-audit, Trivy, and the R10 invariant.
- `.pre-commit-config.yaml` — Ruff, Gitleaks, the R10 check, and a scrub check.

#### Quality & docs
- `tests/test_parity_matrix.py` — capability parity matrix (tools, platforms, runtimes, subsystems, registry) + cyber-skills index regression + deliberate-stub guard.
- Unit tests for every new module (102 passing across the additions).
- Website: a v0.4.0 capabilities doc page wired into the Features sidebar.

### Changed
- Version bumped to 0.6.0 (`pyproject.toml`, `xavani_cli.__version__`, `xavani.VERSION`).

### Notes
- Detection/routing remains model-free (R10), enforced in CI. Deliberate stubs (`skills_hub`, `weixin`) and agent identity are unchanged.

## [0.3.0] - 2025-05-30

### Added

#### Research Guidelines Enforcement
- Expanded mandatory research guidelines from 11 to 21 thinkers.
- New AI/ML thinkers: Chollet, Weng, Huyen, Yan.
- New software craft thinkers: Beck, Hickey, Fowler, Carmack, Kernighan & Pike, Dijkstra.
- Karpathy guidelines strengthened with 4 operating rules (Think-Before-Coding, Simplicity-First, Surgical-Changes, Goal-Driven-Execution).
- CLI: `xavani guidelines list|show|check` subcommand.
- Pre-ship verification gate tool (`guidelines_gate`).

#### New Tools
- `eval_harness` — define, run, and report evaluation cases.
- `mixture_of_agents` — route problems through multiple models collaboratively.
- `computer_use` — drive screen/keyboard/mouse via MCP server.
- `guidelines_gate` — pre-ship verification against research principles.
- Budget governor — per-session token/cost monitoring with threshold warnings.

#### Cybersecurity Skills (754)
- Full import from mukul975/Anthropic-Cybersecurity-Skills (Apache-2.0).
- Covers: threat hunting, incident response, cloud security, red team, forensics, and more.
- Located under `optional-skills/cybersecurity/`.
- Import script: `scripts/import_cybersecurity_skills.py`.
- Attribution: `optional-skills/cybersecurity/NOTICE` and `ATTRIBUTION.md`.

#### Elite Build-and-Ship Skills (10)
- `ship-it-preflight` — pre-release checklist.
- `rfc-writer` — RFC authoring guide.
- `prd-writer` — PRD authoring guide.
- `release-engineering` — release management.
- `perf-profiling` — performance profiling.
- `incident-response` — incident response playbook.
- `api-design-review` — API design review checklist.
- `observability-setup` — observability setup guide.
- `database-migration-playbook` — safe database migrations.
- `secure-by-default-checklist` — security review checklist.

#### Ported Skills (6)
- `tdd` — test-driven development.
- `brainstorming` — structured brainstorming.
- `frontend-design` — frontend design principles.
- `mcp-builder` — MCP server builder.
- `security-review` — security review checklist.
- `verification-before-completion` — verification before declaring done.

#### Infrastructure
- Skill auto-improvement loop (`xavani_learner/skill_improver.py`).
- Hibernation adapters (`tools/environments/hibernation.py`).
- Session budget governor (`agent/budget_governor.py`).

### Changed
- Version bumped from 0.2.0 to 0.3.0.
- README updated with v0.3.0 "What's New" section.
- MANIFEST.md updated with all 21 guideline entries.
- Test contract updated: `EXPECTED_THINKERS` now includes all 21 names.

## [0.2.0] - Previous release

Initial release.
