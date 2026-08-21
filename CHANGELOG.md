# Changelog

All notable changes to Xavani Agent are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-08-21 — "Durability & Capability"

Minor release with durable turn-bank recovery, a faster task harness, and
new business, personal, design, and code-quality skill packs. No breaking
changes.

### Added
- Durable version-2 turn-bank state with count-bound SHA-256 checkpoints,
  pending-sequence proof, compression lineage, and branch isolation.
- Strict restart recovery for stale, malformed, future, and legacy state.
- Canonical transcript selection that stores raw persisted output instead
  of transformed display output.
- Synthetic control-message filters for compression, continuation, kanban,
  empty-response, MCP reload, and maximum-iteration paths.
- Task benchmark harness with median time, p90 time, token use, success rate,
  and cost-per-successful-task metrics.
- Ponytail minimal-code pack with 6 skills and MIT attribution.
- Business assistant, personal assistant, game theory, mental models,
  AI-native UI, and anti-slop TypeScript/JavaScript skills.

### Changed
- Built-in skill indexing now includes local `oag_skills` entries and keeps
  the skills manifest append-only.
- Built-in skill count increased to 181.
- Memory-write results now require `success=true` and `staged` absent or
  exactly `false`.

### Fixed
- Legacy state no longer writes memory when history cannot prove its
  checkpoint.
- Repeated identical turns now use occurrence-aware persistence proof.
- Session changes clear pending state unless a valid compression lineage
  proves continuity.
- Failed due writes retry on each later completed turn.
- Whole-bank proof now binds the header count to the pending base and end.
- An unmatched latest request cannot reuse an older identical response.

## [0.1.1.5] - 2026-08-06 — "Harness & Tokens"

Release with the research-backed harness upgrade, the token vault, and the
completed update programme. No breaking changes.

### Added
- **`xavani tokens` CLI** — one credential vault for all Enternovate products:
  `add`, `list`, `remove`, `show-usage`. Tokens live in
  `~/.xavani/credentials.json` with 0600 permissions; values are never
  printed back. `xavani doctor` now validates the vault (permissions,
  empty entries) in a Token Vault section.
- **Eval gate (harness item 1)** — golden steer-path evals run in CI on any
  PR touching the steer paths (`run_agent.py`, `conversation_loop.py`,
  `agent_init.py`, `cli.py`, harness modules). A failing eval blocks the
  merge. Runner: `scripts/run_golden_evals.py`.
- **Tool-call metrics (harness item 2)** — `agent/tool_metrics.py` records
  one row per tool call (tool, latency ms, success, retries, error class)
  to per-session JSONL/CSV under `~/.xavani/metrics/`. Wired into both
  dispatch paths (concurrent worker and sequential tail); a metrics
  failure can never break tool execution.
- **Self-critique pass (harness item 3)** — `agent/self_critique.py` runs a
  bounded model review of the final answer against a rubric (correctness,
  completeness, citations, STE compliance) and may rewrite it once.
  Config-gated: `harness: {self_critique: true}` in config.yaml (default
  off). Wired at end-of-turn; the reviewer routes through the agent's
  active model configuration; failures keep the original answer.
- **Context-budget governor UI (harness item 4)** —
  `agent/context_budget_ui.py` classifies context usage: warn at 85%
  with a compaction suggestion, block at 95%. Wired into `/usage` and the
  status bar (⚠ at warn, ⛔ at block).
- **Flake dashboard ingestion (harness item 5)** —
  `scripts/flake_dashboard.py` + `tests/test_flake_dashboard.py` aggregate
  flake evidence from fixture runs (Tukey: the data may not contain the
  answer; a visible flake report turns guesswork into measurement).
- **Update programme complete** — every planned reliability item ships
  with test evidence, including D07 sandbox subcommand gating and
  C03/C04/C06 completions.
- **Harness research** — the improvement plan drew on public research
  (Anthropic evals, Red Hat 8-stage, OpenMLE, TraceCompiler, AgentSLABench
  and more) with sources and test plans.

### Changed
- **Pinned 5 dependencies**: pydantic-settings 2.14.2, jsonschema 4.26.0,
  diskcache 5.6.3, structlog 26.1.0, orjson 3.11.9 (locked in uv.lock).
- **`xavani update`** refreshes pinned dependencies with `--upgrade`.
- **README** — removed the stale v0.3.0 section; release notes now match
  the real 0.1.1 / 0.1.1.5 history.

### Fixed
- **D07 sandbox + subcommand gating** — `sandbox` no longer collides with
  built-in subcommands; autostash and gating test expectations updated to
  the `--upgrade` update pipeline (7c6a0ab).
- **CI** — `github-script` action pinned to a resolvable commit SHA
  (v7.1.0).

## [0.1.1] - 2026-08-05 — "Reliability & Steer"

Patch release. Fixes, CI hardening, and the first tranche of the update
programme. No breaking changes.

### Fixed
- **/steer reliability** — end-to-end verification of the steer pipeline (TUI
  `/steer` → gateway `session.steer` → `AIAgent.steer()` → drain into the next
  tool result), including idle fallback to queue, leftover-steer delivery at
  turn end, and a rebuilt TUI bundle.
- **Python 3.14 compatibility** — `_DaemonThreadPoolExecutor` in
  `agent/memory_manager.py` broke against the 3.14 stdlib refactor of
  `concurrent.futures.thread._worker`; `_adjust_thread_count` is now
  version-agnostic (6 memory-manager tests restored).
- **D01 secret redaction regression** — `_redact_content_parts()` mangled
  non-text content parts (e.g. `image_url`) by embedding whole parts as
  nested text; non-text parts now pass through untouched and the identity
  contract (`content is result["content"]`) is preserved when nothing is
  redacted (restores vision-model tool results).
- **D08 subcommand gating** — `deps-provenance` added to
  `_BUILTIN_SUBCOMMANDS` so the CLI fast-path skips plugin discovery for it.
- **Session export timestamps** — export tests computed expectations in the
  ambient timezone while the suite pins TZ=UTC; expectations are now UTC
  (renderer was correct).
- **CI — Windows footgun** — `os.kill(pid, 0)` in `tools/long_running.py`
  replaced with `psutil.pid_exists` (safe on Windows; bpo-14484).
- **CI — Nix** — refreshed the stale `ui-tui` npm-deps hash in `nix/tui.nix`.

### Added (update programme, tranches 1 & 2)
- **E03 Crash forensics** — watchdog + `shutdown_forensics` extension; on
  abnormal exit, last log lines and thread stacks are dumped to
  `~/.xavani/logs/crash-<ts>.txt` (with tests).
- **E04 Memory/disk watchdog** — warn at 80% memory / 90% disk, auto-rotate
  logs past 500 MB (`gateway/memory_monitor.py` extension).
- **E05 Per-session cost CSV export** — `xavani_cli/session_export_csv.py`;
  per-session token/cost rows for accounting.
- **F02 Homebrew formula refresh automation** — CI workflow
  (`.github/workflows/homebrew-refresh.yml`) that bumps
  `packaging/homebrew/xavani-agent.rb` on release.
- **F03 Docker healthcheck** — `HEALTHCHECK` instruction + `docker/healthcheck.sh`
  hitting the gateway `/health` endpoint.
- **G03 Autonomous maintenance window** — `xavani_operator/maintenance.py`:
  idle-time DB VACUUM, log rotation, stale-lock GC (with tests).
- **C02 Model cost guard** — `xavani_cli/model_cost_guard.py`; `/model`
  switches to models above $20/M input tokens now surface a warning via
  `ModelSwitchResult.warning_message` (shared by CLI and gateway).
- **C07 Bang shell** — `!cmd` executes a shell command from the chat line
  (120s timeout, output + exit code printed, never touches the agent).
- **B02 Context breakdown** — `/usage` now shows a per-call breakdown of
  system/conversation/cache tokens (estimates marked, cache counts exact).
- **C08 Prompt stash** — `/stash save|list|show|load|rm`; draft prompts
  persist across sessions under `~/.xavani/prompt-stash/`.

## [0.1.0] - 2026-08-05 — "First Official Release"

The first public release of Xavani Agent. Everything before this date —
internal development builds and pre-release version numbers — has been
consolidated into this single release. Versioning now starts cleanly at
0.1.0; the next release is 0.1.1 (SemVer patch).

Xavani is a fully local, zero-telemetry AI agent gateway: one CLI and TUI to
30+ AI providers, with an MCP gateway, a persistent memory layer, a protocol
bridge, observability, a portable agent runtime, cron jobs, webhooks, and
messaging gateways for Telegram, Discord, Slack and WhatsApp.

### Core platform
- **Agent runtime** — turn-based loop with tool execution, interrupt /
  redirect / steer semantics, stream single-writer fencing, context
  compression, and a deterministic-first (R10) architecture: the LLM only
  *generates*; routing, detection and governance are model-free.
- **MCP gateway** — native Model Context Protocol client/server; register
  external MCP servers as tools; expose the tool registry over MCP.
- **Memory layer** — episodic + procedural memory, hybrid vector/full-text
  search, zero-cloud, durable across sessions (the Ndlovu memory engine).
- **Providers** — 30+ OpenAI-compatible and native providers with an
  intelligent model router (`xavani model --route <task>`).
- **Messaging gateways** — Telegram, Discord, Slack, WhatsApp (+ more);
  slash commands, sessions, approvals, and per-platform auth.
- **Cron, webhooks, delegation** — scheduled jobs, inbound webhooks,
  sub-agent orchestration with context isolation.
- **Skill system** — 169+ skills, reusable procedural memory, skill
  auto-improvement loop, and a skills index.
- **Tools** — 90+ tools including `read_document`, `eval_harness`,
  `mixture_of_agents`, `computer_use`, `guidelines_gate`, `process`,
  `session_search`, `organize_files`, and a budget governor.

### Sentience & wisdom (deterministic, zero-LLM at the core)
- **Quantum Decision Cortex** (`xavani_operator/quantum/`) — decisions held in
  superposition, outcomes simulated, correlated risks interfered, collapse by
  Born rule; classical solver always on, optional QPU backends.
- **The Oracle** (`xavani_wisdom/`) — consequence projector, downfall
  detector, self-fault watch-patterns from the 8pm error-log ritual.
- **Always-On Companion** — 24/7 daemon (`xavani operator serve`),
  kill-switch, advisor rituals (morning brief, 8pm error-log, tomorrow plan,
  hourly task-chase), intelligent model router.
- **Mission Control** — deep-navy dashboard with Sentience page, quantum
  waveform, and Oracle consequence-check.

### The complete update programme (implemented, tested, verified)
A Reliability & Correctness (20) · B Intelligence & Reasoning (15) ·
C Operability & Developer Experience (20) · D Safety & Guardrails (15) ·
E Observability & Debugging (10) · F Distribution & Ecosystem (10) ·
G Autonomy & Proactivity (10). Highlights:
- Turn leases, session redirect with lock, turn persistence drain, bounded
  responses, session-store recovery + FTS rebuild, code-skew detection,
  restart-loop guard, systemd readiness.
- Chain-of-thought budget enforcement, context-breakdown widget, learn
  prompt pack, delegation context isolation, subagent lifecycle API.
- Unified provider catalog, model cost guard, `xavani security-audit`,
  secrets vault CLI, session recovery, update pipeline with lock, bang
  shell, prompt stash.
- Secret redaction on tool output, PII redaction parity, egress policy
  enforcement, Tirith command-guard, credential rotation reminders,
  append-only mutation audit, dependency provenance report.
- Gateway health export, turn timeline trace, crash forensics, memory/disk
  watchdog, per-session cost CSV, flake dashboard.
- ACP server hardening, Homebrew refresh automation, Docker healthcheck,
  Windows portable installer, Nix flake cache, skills freshness watchdog.
- Smart notifications, daily learning digest, autonomous maintenance,
  follow-up question queue.

### Security & privacy
- Zero telemetry, local-first, keys stay on the machine.
- Egress allowlist, sandbox hardening (rlimits, seccomp/Landlock detection),
  RLS-ready multi-tenant design, encryption at rest/in transit, audit
  trail on AI actions.
- CI security stack: Bandit, Gitleaks, Semgrep, pip-audit, Trivy, OSV
  scanner, supply-chain audit, dependency provenance, and the R10
  deterministic invariant enforced in tests.

### Distribution
- PyPI wheel (`pip install xavani-agent`), Homebrew formula, Docker image
  with HEALTHCHECK, Nix flake + Cachix cache, Windows portable installer,
  one-line installers (`curl -fsSL https://get.xavani.dev | bash`).
- MIT licensed. Derived from Hermes Agent by Nous Research (MIT) with
  attribution; maintained independently by Enternovate.
