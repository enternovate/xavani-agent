# Xavani Agent — 50 Major Updates Brainstorm (Round 2)

Date: 2026-08-04
Source: gap reports vs Hermes v0.19.1 + production-readiness audit + the
100-update program's completed tranches
Lenses: reliability, intelligence, security, operability, distribution, autonomy
Legend: S <1 day | M 1-3 days | L 1-2 weeks | XL >2 weeks

## A. Reliability & Correctness (10 items)

A01. Session redirect with lock (port Hermes run_agent.py:3003-3090)
  What: /stop→new-session handoff with _pending_redirect_lock so a hard stop
        cannot race an accepted correction into a retry.
  Where: run_agent.py interrupt()/clear_interrupt()
  Why: Reported gap #1 in the core-loop audit. Eff: M

A02. Stream single-writer fence (port agent/stream_single_writer.py)
  What: Claim the stream writer per turn so superseded streams cannot emit
        interleaved tokens to the TUI/gateway.
  Where: run_agent.py stream callbacks + tui_gateway
  Why: Reported gap. Prevents ghost text after interrupts. Eff: M

A03. Turn persistence drain with locking (port _persist_and_drain)
  What: Locked flush + drain at turn end, mirroring Hermes run_agent.py:1884.
  Where: run_agent.py _persist_session
  Why: Session-DB writes under concurrent gateway streams. Eff: M

A04. Turn finalizer/retry-state extraction
  What: Split the monolithic conversation_loop tail into
        agent/turn_finalizer.py + turn_retry_state.py (Hermes has these).
  Where: agent/conversation_loop.py
  Why: The loop is 4,237 lines; the tail has 6+ exit paths. Testability. Eff: M

A05. Bounded-response coverage sweep
  What: Find every remaining response.read()/urlopen() in tools/ and gateway/
        without a timeout or byte cap; apply agent/bounded_response.py.
  Where: tools/*.py, gateway/*.py
  Why: A07's timeout-guard everywhere. Eff: M

A06. Session store recovery + FTS rebuild (port AsyncSessionStore pieces)
  What: On gateway start, verify the session DB is intact; rebuild FTS index
        if corrupt; recover sessions from WAL.
  Where: gateway/session.py, xavani_state.py
  Why: Hermes has 3,344 lines here vs Xavani 1,413. Eff: L

A07. Turn lease (per-turn concurrency guard)
  What: One active turn per session key; reject/queue a second before it
        double-fires the model.
  Where: gateway/run.py
  Why: Gateway reliability module list. Eff: M

A08. Code-skew detection (port gateway/code_skew.py)
  What: Detect when a long-running gateway's code differs from HEAD and warn.
  Where: gateway/run.py startup
  Why: Prevent "I fixed it but the bot runs old code" confusion. Eff: S

A09. Restart loop guard (port gateway/restart_loop_guard.py)
  What: Count restarts in a window; if the gateway crashes 5+ times in 5 min,
        stop and surface the error instead of crash-looping.
  Where: gateway/run.py
  Why: Gateway reliability. Eff: S

A10. Systemd notify + readiness (port gateway/systemd_notify.py, readiness.py)
  What: sd_notify READY=1 when the gateway is up; readiness endpoint for
        orchestrators.
  Where: gateway/run.py + packaging/systemd/
  Why: Production deployment on Linux servers. Eff: S

## B. Intelligence & Reasoning (8 items)

B01. Chain-of-thought budget enforcement (agent-side, full)
  What: Enforce max_reasoning_tokens per model family from
        agent/reasoning_timeouts.py-style database; expose in config.
  Where: agent/agent_init.py, xavani_cli/timeouts.py
  Why: Cost control on reasoning models. Eff: M

B02. Context breakdown widget
  What: Per-call breakdown of system/context/volatile tokens in /usage
        (port agent/context_breakdown.py).
  Where: cli.py /usage, xavani_cli/web_server.py
  Why: Users need to see where tokens go. Eff: S

B03. Message content utilities (port agent/message_content.py)
  What: Shared text-extraction/attachment helpers across transports.
  Where: agent/message_content.py (new)
  Why: Deduplicate 6+ ad-hoc content walkers. Eff: S

B04. Learn prompt pack (port agent/learn_prompt.py)
  What: Structured "teach the agent" prompt that extracts a rule + example
        from a user correction and files it as a skill draft.
  Where: agent/learn_prompt.py + cli.py /learn
  Why: Makes corrections durable. Eff: M

B05. Episodic memory summarization into MEMORY.md
  What: Weekly job that reads xavani_memory episodes and proposes MEMORY.md
        entries for promotion.
  Where: xavani_memory/manager.py + cron
  Why: Close the loop between episodic store and declarative memory. Eff: M

B06. Reasoning-effort auto-tuning per task
  What: Route simple tasks (file ops) to low reasoning effort, complex tasks
        to high — using the existing model_router capability map.
  Where: model_router.py + agent/agent_init.py
  Why: Cost/latency win with no accuracy loss on simple tasks. Eff: M

B07. Delegation context isolation (port agent/delegation_context.py)
  What: Explicit child-session context (parent session id, cwd, profile) so
        subagents cannot leak state across delegations.
  Where: agent/delegation_context.py + delegate_task tool
  Why: Reported gap #34. Eff: M

B08. Subagent lifecycle API (port agent/subagent_lifecycle.py)
  What: Public plugin-safe lifecycle contract for supervising children.
  Where: agent/subagent_lifecycle.py (new)
  Why: Plugin ecosystem needs a stable boundary. Eff: M

## C. Operability & Developer Experience (8 items)

C01. Unified provider catalog (port hermes_cli/provider_catalog.py)
  What: Single catalog of all 33 providers with setup wizards, shared by CLI
        picker, TUI, and web settings.
  Where: xavani_cli/provider_catalog.py (new)
  Why: Reported gap. Eff: M

C02. Model cost guard
  What: Confirm before switching to models whose per-M token cost exceeds
        $20/$100 (port hermes_cli/model_cost_guard.py).
  Where: xavani_cli/model_switch.py
  Why: Prevents accidental expensive-model switches. Eff: S

C03. Security audit command (port hermes_cli/security_audit.py)
  What: `xavani security-audit` — OSV check + venv scan + plugin/MCP scan in
        one command with a JSON report.
  Where: xavani_cli/security_audit.py (new)
  Why: Reported gap #53. Eff: M

C04. Secrets vault CLI (port hermes_cli/secrets_cli.py)
  What: `xavani secrets` — Bitwarden/1Password/command secret sources with
        registry fallback.
  Where: xavani_cli/secrets_cli.py (new)
  Why: Reported gap #54. Eff: M

C05. Session export recovery (port hermes_cli/session_recovery.py)
  What: Recover sessions from a corrupted DB file by scanning WAL + journal.
  Where: xavani_state.py
  Why: Data-loss protection. Eff: M

C06. Update pipeline with lock (port hermes_cli/update_cmd.py pieces)
  What: `xavani update` with updater lock + service restart orchestration.
  Where: xavani_cli/update_cmd.py
  Why: Reported gap. Eff: L

C07. Bang shell (port hermes_cli/bang_shell.py)
  What: `!cmd` executes shell commands from the chat line.
  Where: cli.py process_command
  Why: Reported gap. Eff: S

C08. Prompt stash (port hermes_cli/prompt_stash.py)
  What: Save/restore draft prompts across sessions (/stash).
  Where: cli.py + xavani_cli/prompt_stash.py
  Why: Reported gap. Eff: M

## D. Security & Privacy (8 items)

D01. Secret redaction on tool output (config-gated)
  What: security.redact_secrets toggle that masks API-key-shaped strings in
        tool results before they enter context.
  Where: agent/agent_init.py or tool_result pipeline
  Why: Defense in depth on shared machines. Eff: M

D02. PII redaction parity check
  What: Audit all gateway platform adapters for PII (phone, email, ID) that
        reaches prompts; extend _PII_SAFE_PLATFORMS where safe.
  Where: gateway/platforms/*.py
  Why: Privacy at an all-time high. Eff: M

D03. Egress policy enforcement at the socket layer
  What: Wire tools/egress_policy.py into the httpx transport so outbound
        hosts outside the allowlist fail closed.
  Where: agent/async_utils.py / client factories
  Why: tools/egress_policy.py exists but is not enforced at the socket. Eff: L

D04. Tirith command-guard default-on for gateway
  What: Enable tirith scanning for gateway-spawned commands by default with
        fail-open until binary lands (verified fix pattern).
  Where: tools/tirith_security.py
  Why: The gateway is the highest-risk surface. Eff: S

D05. Credential rotation reminders
  What: Warn when an API key is older than 90 days (hash-stored, no plaintext).
  Where: xavani_cli/doctor.py
  Why: Hygiene. Eff: S

D06. Audit log for memory/skill writes
  What: Append-only JSONL of memory + skill mutations with origin
        (assistant_tool vs background_review).
  Where: tools/memory_tool.py, tools/skill_manager_tool.py
  Why: Traceability; pairs with write_approval gate. Eff: S

D07. Sandboxed terminal default for untrusted projects
  What: When TERMINAL_CWD points at a git repo with no owner, run commands in
        a container/docker sandbox by default.
  Where: tools/terminal_tool.py
  Why: Supply-chain defense. Eff: L

D08. Dependency provenance report
  What: `xavani deps-provenance` — list every direct dep with its source
        (PyPI/git fork), hash, and last audit date.
  Where: xavani_cli/deps_provenance.py (new)
  Why: Supply-chain transparency; surfaced the discord fork pin already. Eff: S

## E. Observability & Debugging (6 items)

E01. Gateway health export (port gateway/gateway_health_export.py)
  What: /health endpoint + prometheus-exportable health state.
  Where: gateway/run.py + xavani_observability/prometheus.py
  Why: Reported gap. Eff: M

E02. Turn timeline trace
  What: Per-turn trace (user msg → model call → tools → final) with
        durations, exported as JSONL for debugging.
  Where: agent/trajectory.py
  Why: Makes "why did the agent do X" answerable. Eff: M

E03. Crash forensics (port gateway/shutdown_forensics.py)
  What: On abnormal exit, dump last N log lines + thread stacks to
        ~/.xavani/logs/crash-<ts>.txt.
  Where: xavani.py + gateway/run.py
  Why: Xavani already has shutdown_forensics.py — verify and extend. Eff: S

E04. Memory/disk watchdog
  What: Warn at 80% memory and 90% disk; auto-rotate logs when >500MB.
  Where: gateway/memory_monitor.py (exists — extend)
  Why: Production ops. Eff: S

E05. API cost per session CSV export
  What: Export per-session token/cost rows to CSV for accounting.
  Where: xavani_state.py + xavani_cli/sessions_cmd.py
  Why: Billing reconciliation. Eff: S

E06. Flake dashboard
  What: Parse tests/flakiness.json into a CI artifact page (top flaky tests,
        root-cause labels).
  Where: .github/workflows + website
  Why: A19's data needs a home. Eff: S

## F. Distribution & Ecosystem (6 items)

F01. ACP server hardening
  What: Full ACP (Agent Client Protocol) test matrix in CI — version sync,
        manifest validity, tool round-trip.
  Where: acp_adapter/ + .github/workflows
  Why: IDE integrations depend on ACP stability. Eff: M

F02. Homebrew formula refresh automation
  What: CI job that bumps packaging/homebrew/xavani-agent.rb on release.
  Where: .github/workflows/release.yml
  Why: Homebrew users currently get stale versions. Eff: S

F03. Docker image healthcheck
  What: HEALTHCHECK instruction in Dockerfile hitting the gateway /health.
  Where: Dockerfile
  Why: Container orchestrators need liveness. Eff: S

F04. Windows portable installer
  What: scripts/install.ps1 portable Git + Node fallbacks (no admin).
  Where: scripts/install.ps1
  Why: Reported gap D5. Eff: M

F05. Nix flake cache
  What: Cachix CI so nix users get binaries instead of builds.
  Where: .github/workflows/nix.yml
  Why: Nix adoption. Eff: M

F06. Skills freshness watchdog
  What: Every-4h workflow that opens an issue when the live skills index is
        stale (port Hermes skills-index-freshness.yml).
  Where: .github/workflows/skills-index-freshness.yml
  Why: Reported gap C5. Eff: S

## G. Autonomy & Proactivity (4 items)

G01. Smart notifications (extend)
  What: Route important gateway events (crash, funding hit, approval stuck)
        to the user's preferred platform proactively.
  Where: xavani_cli/notifications.py + gateway/run.py
  Why: G07 from round 1 needs event wiring. Eff: M

G02. Daily learning digest
  What: Cron job that summarizes the day's episodes from xavani_memory and
        proposes skill updates.
  Where: cron + xavani_memory/manager.py
  Why: Turns the episodic store into weekly growth. Eff: M

G03. Autonomous maintenance window
  What: When idle, run maintenance: DB VACUUM, log rotation, stale-lock GC,
        skill usage refresh.
  Where: xavani_operator/daemon.py
  Why: Self-healing. Eff: S

G04. Follow-up question queue
  What: When the agent finishes a task with open questions, queue them and
        surface at a good moment instead of blocking.
  Where: agent/conversation_loop.py + cli.py
  Why: Politeness + momentum. Eff: M

## Implementation Priority (top 20 by impact/effort)

 1. D03 egress enforcement (L)         11. C01 provider catalog (M)
 2. A01 session redirect (M)           12. A05 bounded-response sweep (M)
 3. A06 session recovery (L)           13. D04 tirith default-on (S)
 4. A03 persist drain lock (M)         14. B05 episodic→MEMORY promotion (M)
 5. A02 stream writer fence (M)        15. E01 health export (M)
 6. D01 secret redaction (M)           16. C03 security audit cmd (M)
 7. B01 reasoning budget (M)           17. F06 skills freshness watchdog (S)
 8. A07 turn lease (M)                 18. E06 flake dashboard (S)
 9. A10 systemd readiness (S)          19. B04 learn prompt pack (M)
10. C04 secrets vault (M)              20. G02 daily learning digest (M)
