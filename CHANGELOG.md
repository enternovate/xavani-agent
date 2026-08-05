# Changelog

All notable changes to Xavani Agent are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - Unreleased — "Reliability & Steer"

Patch release. Fixes, CI hardening, and the first tranche of the 50-update
program (XAVANI_50_UPDATES.md). No breaking changes.

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

### Added (50-update program, tranches 1 & 2)
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

### The 100-update program (fully implemented, tested, verified)
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
