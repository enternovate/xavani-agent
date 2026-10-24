> **CLOSED-SUPERSEDED 2026-10-24.** Evidence: `docs/CLOSURE-0.3.1.md`.
> Successor: `planning/reliability-master-plan.md`.

# Xavani Agent Quality and Performance Roadmap

> **For Hermes:** Use the `subagent-driven-development` skill to implement this plan task by task.

**Goal:** Complete E103 first. Then deliver 100 measured Xavani quality, speed, cache, security, privacy, and usability updates.

**Architecture:** The parent agent owns all design decisions and final evidence. Paid DeepSeek V4 Flash subagents act as bounded planners, builders, and reviewers.

**Tech Stack:** Python 3.11+, pytest, Ruff, ty, SQLite, Git, OpenCode Zen, DeepSeek V4 Flash, Node.js, and the Xavani plugin system.

---

## 1. Authority and Worker Model

The parent agent is the design lead and final authority.

The parent agent shall:

- Read all relevant source files.
- Define the architecture.
- Define the exact scope.
- Define the acceptance criteria.
- Write each worker prompt.
- Verify each worker claim.
- Reject weak or speculative work.
- Verify the final diff and test evidence.

Subagents shall use:

- Provider: `opencode-zen`.
- Model: `deepseek-v4-flash`.
- Maximum concurrency: `3`.
- Shared-file concurrency: `1`.
- Required output schemas.
- Exact file ownership.
- Exact verification commands.

A subagent verdict does not replace parent verification.

A missing or malformed subagent result counts as no verdict.

## 2. Current Repository State

Repository:

`/Users/andilemushwana/xavani-agent`.

Current branch:

`main`.

Current commit:

`1af70489e1d9f33d0140754f1b2d6af3f5e4df6c`.

The branch is 81 commits ahead of `origin/main`.

The working tree contains 33 changed or untracked paths.

The E103 scope contains only these project files:

- `agent/turn_bank.py`.
- `tests/run_agent/test_turn_bank.py`.

Preserve all unrelated paths.

Do not reset the tree.

Do not stash the tree.

Do not use `git add -A`.

Do not use `git add .`.

Do not commit without separate approval.

## 3. E103 Work Order

Use the existing E103 plan as the implementation authority:

`.hermes/plans/2026-08-13_162744-e103-durable-state-quality-control.md`.

The E103 plan now uses paid `deepseek-v4-flash`.

The goal verifier now reports `STRONG` with `34/42`.

The assumption linter reports 5 known false positives.

The E103 plan records a line-by-line disposition for those 5 findings.

The independent plan approval remains the active blocker.

Map the remaining 14 workflow items to the 18 task headings as follows:

- Obtain independent plan approval through Task 2.
- Add memory gate tests through Task 3.
- Add legacy state tests through Task 4.
- Implement state version 2 through Task 5.
- Add stale state tests through Task 6.
- Implement checkpoint recovery through Tasks 7, 7A, and 7B.
- Add strict memory proof tests through Tasks 8 and 9.
- Verify strict memory proof through Task 10.
- Run focused integration gates through Task 11.
- Obtain specification approval through Task 12.
- Obtain quality approval through Task 13.
- Run the complete suite through Task 14.
- Verify the wheel, secrets, and scope through Task 15.
- Obtain integration approval and commit approval through Tasks 16 and 17.

Do not start Task 3 before Task 2 receives an explicit `APPROVED` verdict.

Require empty issue arrays with that verdict.

## 4. E103 Verification Commands

Run the assumption linter:

```bash
python3 /Users/andilemushwana/.hermes/skills/claude-plugins/engineering-advanced-skills/2.3.0/karpathy-coder/scripts/assumption_linter.py --json .hermes/plans/2026-08-13_162744-e103-durable-state-quality-control.md
```

Expected result:

- The report contains 5 documented false positives.
- The plan contains a disposition for all 5 findings.

Run the goal verifier:

```bash
python3 /Users/andilemushwana/.hermes/skills/claude-plugins/engineering-advanced-skills/2.3.0/karpathy-coder/scripts/goal_verifier.py --json .hermes/plans/2026-08-13_162744-e103-durable-state-quality-control.md
```

Expected result:

- Verdict: `STRONG`.
- Score: `34/42` or higher.
- Missing verification steps: `0`.

Run E103 tests only in the order from the E103 plan.

Run the complete suite only at Task 14.

## 5. External Source Decisions

### 5.1 Anti-slop

Source:

`dmmulroy/anti-slop`.

License:

`MIT`.

Decision:

Install the skill in both agent environments after a security audit.

Do not run the Oxlint installer against the Python repository root.

The Oxlint plugin applies only to TypeScript and JavaScript projects.

Use this command to inspect the available skill:

```bash
npx skills add dmmulroy/anti-slop --list
```

Use this command after the audit:

```bash
npx skills add dmmulroy/anti-slop --skill install-anti-slop
```

Verify the selected target before the installer writes files.

Install the skill into the Xavani skill environment.

Install the skill into the Hermes skill environment.

Evaluate Oxlint adoption only for owned TypeScript and JavaScript surfaces.

### 5.2 Ponytail

Source:

`DietrichGebert/ponytail`.

License:

`MIT`.

Decision:

Install the native plugin in Xavani and Hermes after a security audit.

Use this Xavani command:

```bash
xavani plugins install DietrichGebert/ponytail --enable
```

Use this Hermes command:

```bash
hermes plugins install DietrichGebert/ponytail --enable
```

Keep the global mode off by default.

Use `full` mode for builder tasks.

Use `review` mode for reviewer tasks.

Keep Ponytail instructions below mandatory security, privacy, and validation rules.

### 5.3 BTW side channel

Source:

`mitsuhiko/agent-stuff/extensions/btw.ts`.

License:

`Apache-2.0`.

Decision:

Adapt the design. Do not copy the Pi-specific TypeScript implementation.

Xavani currently maps `/btw` to `/background`.

The new `/btw` shall provide a bounded side conversation with a summary handoff.

The `/background` command shall keep its current full background task behavior.

Provide a migration note for the changed `/btw` behavior.

### 5.4 Pi compaction article

Source:

`https://earendil.com/posts/compaction-in-pi/`.

Apply these verified principles:

- Compact after a turn when possible.
- Use a standalone summary request.
- Use a distinct summary instruction.
- Keep a configurable recent token budget.
- Store the summary as portable plain text.
- Measure the cache break after compaction.
- Restore cache use on the next request.

## 6. Security Gate for External Sources

Before each installation:

1. Record the upstream commit hash. Verify: `git ls-remote` returns one 40-character commit.
2. Run the skill security auditor. Verify: the report contains no unaccepted high or critical finding.
3. Inspect scripts and lifecycle hooks. Verify: the audit lists each executable entry point.
4. Inspect network calls. Verify: the audit lists each remote destination.
5. Inspect file writes. Verify: the audit lists each destination path.
6. Inspect prompt injection risks. Verify: no source text overrides mandatory host rules.
7. Verify the license. Verify: the repository license matches the recorded license.
8. Verify the destination path. Verify: the path stays inside the selected agent profile.
9. Install after an accepted audit. Verify: the installed tree matches the audited source hash.
10. Record the installed commit hash. Verify: the installed hash equals the upstream hash.

Do not accept an automatic install from an unreviewed branch.

Do not expose credentials in an audit report.

## 7. Performance Metric Contract

Define these metrics before an optimization:

- `stable_prefix_cache_rate` measures cached eligible prefix tokens.
- `raw_cache_ratio` measures cached tokens divided by all prompt tokens.
- `cold_start_cache_ratio` measures the first request separately.
- `warm_cache_ratio` measures requests after the first request.
- `cache_break_cost` measures uncached tokens after compaction.
- `ttft_p50` measures median time to the first token.
- `ttft_p95` measures the 95th percentile time to the first token.
- `turn_latency_p50` measures median complete turn time.
- `turn_latency_p95` measures the 95th percentile complete turn time.
- `task_throughput` measures completed tasks per hour.
- `pass_at_1` measures first-pass task acceptance.
- `pass_at_3` measures acceptance after 3 evidence gates.
- `compaction_fidelity` measures retained seeded facts.
- `flake_rate` measures unstable test outcomes.

The 99% target applies only to stable prefix tokens after warm-up.

Do not claim a 99% raw prompt cache ratio without provider evidence.

## 8. Latency Requirement Conflict

The phrase “minimum 150 seconds per task” conflicts with the low latency goal.

Do not enforce this number until Andile confirms its meaning.

Use this recommended interpretation:

- Target median task time: `150 seconds or less`.
- Keep complex tasks unbounded by quality needs.
- Measure speed after correctness passes.
- Do not delay a completed task to meet a minimum duration.

## 9. Curated 100 Updates

The 2 subagents proposed 109 updates.

The parent rejected 9 weak or duplicate updates.

The rejected updates proposed costly keep-alive calls, invalid chronology, unproved cache sharing, or unsafe streaming.

The 100 accepted updates follow.

### H001. Define the stable prefix cache metric.

- Problem: The current cache ratio has no stable denominator.
- Files: `agent/conversation_loop.py`, `run_agent.py`, `xavani_state.py`, and `cli.py`.
- Gate: Persist the stable ratio and the raw ratio across a restart.

### H002. Persist cache counters safely.

- Problem: A process restart loses current cache counters.
- Files: `run_agent.py`, `xavani_state.py`, and `agent/turn_finalizer.py`.
- Gate: A restart test shall preserve all recorded counters.

### H003. Select cache boundaries from turn mutations.

- Problem: Fixed trailing breakpoints can include volatile messages.
- Files: `agent/prompt_caching.py` and `agent/conversation_loop.py`.
- Gate: A multi-turn test shall keep the guarded prefix unchanged.

### H004. Cache the byte-stable tool schema block.

- Problem: Schema rebuilds add hot-path work and cache risk.
- Files: `model_tools.py`, `tools/registry.py`, and `agent/chat_completion_helpers.py`.
- Gate: Identical tool sets shall produce identical bytes.

### H005. Detect system prompt drift.

- Problem: Prompt drift silently breaks provider cache use.
- Files: `agent/conversation_loop.py` and `tests/run_agent/test_run_agent.py`.
- Gate: A test shall detect one changed prompt byte.

### H006. Normalize cache reporting across providers.

- Problem: Providers report cached tokens through different response shapes.
- Files: `agent/conversation_loop.py`, `run_agent.py`, `agent/transports/base.py`, `agent/transports/anthropic.py`, `agent/transports/chat_completions.py`, `agent/transports/bedrock.py`, and `agent/transports/codex.py`.
- Gate: All supported response shapes shall produce one canonical cache record.

### H007. Complete the Pi-style compaction contract.

- Problem: The summary call needs a distinct and testable system role.
- Files: `agent/context_compressor.py` and `agent/auxiliary_client.py`.
- Gate: The summary request shall exclude the main agent role and tools.

### H008. Test asynchronous compaction as a spike.

- Problem: Synchronous compaction can block the next visible turn.
- Files: `agent/context_compressor.py` and `agent/conversation_loop.py`.
- Gate: The spike shall prove race safety before production adoption.

### H009. Recover from a mid-turn context overflow.

- Problem: A context overflow can stop an active tool loop.
- Files: `agent/conversation_loop.py` and `agent/error_classifier.py`.
- Gate: A simulated overflow shall compact once and retry once.

### H010. Configure the retained tail budget.

- Problem: The retained token budget uses fixed defaults.
- Files: `cli.py` and `agent/context_compressor.py`.
- Gate: Invalid budgets shall fail configuration validation.

### H011. Replace the hard compaction skip with bounded adaptation.

- Problem: Two weak compactions can block all later recovery.
- Files: `agent/context_compressor.py`.
- Gate: The compressor shall adapt once and then stop safely.

### H012. Protect the active cache boundary during pruning.

- Problem: Tool result pruning can mutate cached history.
- Files: `agent/context_compressor.py` and `agent/prompt_caching.py`.
- Gate: Pruning shall not change bytes inside the guarded prefix.

### H013. Persist iterative summary state.

- Problem: A restart can lose the previous summary delta.
- Files: `agent/context_compressor.py` and `xavani_state.py`.
- Gate: The second compaction shall reuse the restored summary.

### H014. Verify summary portability across model switches.

- Problem: A provider switch can trigger unnecessary summary work.
- Files: `agent/context_compressor.py`, `run_agent.py`, and `tests/run_agent/test_switch_model_context.py`.
- Gate: A plain text summary shall survive a model switch unchanged.

### H015. Add a compaction watchdog.

- Problem: A summary request can block a turn for an unbounded period.
- Files: `agent/api_call_watchdog.py`, `agent/context_compressor.py`, and `cli.py`.
- Gate: A timeout shall abort safely without context loss.

### H016. Reuse verified context limits after failover.

- Problem: A provider failover can discard a verified context limit.
- Files: `agent/model_metadata.py`, `agent/context_compressor.py`, and `agent/model_router.py`.
- Gate: The verified limit shall survive a compatible failover.

### H017. Validate a summary before the context swap.

- Problem: A malformed summary can damage session continuity.
- Files: `agent/context_compressor.py` and `agent/redact.py`.
- Gate: Invalid summaries shall leave the original messages unchanged.

### H018. Serialize cache counter updates.

- Problem: Concurrent workers can lose or duplicate counter updates.
- Files: `run_agent.py`, `agent/stream_single_writer.py`, and `tools/delegate_tool.py`.
- Gate: A race test shall produce exact totals.

### H019. Cache account usage away from the turn path.

- Problem: Account usage requests can block status and turn output.
- Files: `agent/account_usage.py` and `cli.py`.
- Gate: Status shall use a bounded cached snapshot.

### H020. Audit provider connection reuse.

- Problem: New connections add avoidable request latency.
- Files: `agent/auxiliary_client.py`, `agent/transports/anthropic.py`, `agent/transports/chat_completions.py`, `agent/transports/bedrock.py`, and `agent/transports/codex.py`.
- Gate: Each supported provider shall reuse one session transport.

### H021. Add a safe single-turn fast path.

- Problem: Short tasks pay for nonessential background work.
- Files: `agent/conversation_loop.py`, `agent/background_review.py`, and `agent/turn_finalizer.py`.
- Gate: The fast path shall keep all security and approval checks.

### H022. Route with cache-adjusted latency.

- Problem: The model router ignores a warm provider prefix.
- Files: `agent/model_router.py` and `agent/auxiliary_client.py`.
- Gate: A warm provider shall receive a measured routing benefit.

### H023. Refresh credentials before expiry.

- Problem: A token refresh can block the first request.
- Files: `xavani_cli/auth.py` and `agent/credential_pool.py`.
- Gate: One refresh worker shall prevent duplicate refreshes.

### H024. Benchmark per-turn hot functions.

- Problem: Current benchmarks cover imports but not the active turn path.
- Files: `scripts/benchmark.py` and `scripts/benchmark-baseline.json`.
- Gate: CI shall detect a 20% p95 regression.

### H025. Add an end-to-end faux provider benchmark.

- Problem: The repository lacks a deterministic turn latency benchmark.
- Files: `scripts/benchmark.py` and `tests/harness/faux_provider.py`.
- Gate: The benchmark shall record latency, cache ratio, and success.

### H026. Add a cache break regression gate.

- Problem: Compaction cache loss has no automated budget.
- Files: `scripts/compaction_eval/runner.py` and `tests/test_compaction_eval.py`.
- Gate: CI shall reject a larger uncached post-compaction prefix.

### H027. Add a throughput benchmark.

- Problem: Turn speed does not prove task throughput.
- Files: `scripts/benchmark.py` and `scripts/edit_benchmark/runner.py`.
- Gate: The benchmark shall report completed tasks per hour.

### H028. Add an optional live compaction evaluation.

- Problem: The deterministic evaluation does not measure summary model quality.
- Files: `scripts/compaction_eval/runner.py`.
- Gate: The live evaluation shall remain outside required CI.

### H029. Add a cache and compaction race test.

- Problem: Parent and child work can overlap with compaction.
- Files: `tests/stress/` and `tools/delegate_tool.py`.
- Gate: The test shall detect counter loss and summary duplication.

### H030. Canonicalize tool schema JSON.

- Problem: Equivalent schemas can produce different serialized bytes.
- Files: `tools/registry.py` and `tools/schema_sanitizer.py`.
- Gate: Equivalent schemas shall produce one digest.

### H031. Connect the optional tool prefilter.

- Problem: A normal turn can send the complete tool set.
- Files: `tools/tool_prefilter.py`, `model_tools.py`, and `cli.py`.
- Gate: Unknown intent shall restore the complete tool set.

### H032. Lock the retry reset after compaction.

- Problem: A future change can restore stale retry counters.
- Files: `tests/run_agent/test_run_agent.py` and `agent/conversation_loop.py`.
- Gate: The regression test shall verify a fresh retry budget.

### H033. Show cache and latency metrics in the context panel.

- Problem: Operators cannot see progress toward the cache target.
- Files: `agent/context_budget_ui.py` and `cli.py`.
- Gate: The panel shall show cold, warm, and raw ratios.

### H034. Isolate review budgets from visible turns.

- Problem: Background review can consume visible turn time.
- Files: `agent/self_critique.py`, `agent/background_review.py`, and `agent/iteration_budget.py`.
- Gate: Review work shall run after final response delivery.

### H035. Warn before a planned compaction.

- Problem: Operators cannot see a pending context reduction.
- Files: `agent/conversation_loop.py` and `cli.py`.
- Gate: The warning shall appear before the configured threshold.

### H036. Detect repeated low-value tool calls.

- Problem: Repeated identical tool calls waste latency and context.
- Files: `agent/iteration_budget.py` and `agent/tool_executor.py`.
- Gate: The detector shall warn without blocking a valid retry.

### H037. Add per-model reasoning budgets.

- Problem: Unlimited reasoning can delay the first token.
- Files: `agent/model_metadata.py`, `agent/bounded_response.py`, and `cli.py`.
- Gate: Hard tasks shall allow an explicit high-budget override.

### H038. Add a multi-turn cache invariant test.

- Problem: No complete test protects the stable request prefix.
- Files: `tests/run_agent/test_run_agent.py` and `tests/harness/faux_provider.py`.
- Gate: The test shall hash each stable prefix.

### H039. Bound child context growth.

- Problem: A child can waste time on repeated compaction.
- Files: `tools/delegate_tool.py` and `agent/context_compressor.py`.
- Gate: The parent shall receive each child compaction event.

### H040. Derive drain limits from measured latency.

- Problem: Static timeouts do not use observed provider latency.
- Files: `cli.py`, `gateway/run.py`, and `agent/model_router.py`.
- Gate: Dynamic limits shall use safe minimum and maximum clamps.

### H041. Bound memory recall latency.

- Problem: Memory recall can delay a turn and return excessive context.
- Files: `xavani_memory/manager.py` and `agent/conversation_loop.py`.
- Gate: Recall shall enforce entry and token budgets.

### H042. Keep resume notes cache stable.

- Problem: A resume note can shift the stable prefix.
- Files: `gateway/run.py`, `agent/prompt_caching.py`, and `agent/conversation_loop.py`.
- Gate: A resume test shall preserve the previous prefix hash.

### H043. Use one cache capability contract across transports.

- Problem: Provider-specific layouts can diverge silently.
- Files: `agent/prompt_caching.py`, `agent/transports/base.py`, `agent/transports/anthropic.py`, `agent/transports/chat_completions.py`, `agent/transports/bedrock.py`, and `agent/transports/codex.py`.
- Gate: Each transport shall declare its supported cache controls.

### H044. Harden cache marker insertion.

- Problem: Multi-part content can receive an unstable marker shape.
- Files: `agent/prompt_caching.py` and prompt caching tests.
- Gate: Strings, lists, empty content, and tool roles shall stay deterministic.

### H045. Extend compaction evaluation to tools and media.

- Problem: The current evaluation uses a linear text conversation.
- Files: `scripts/compaction_eval/runner.py` and `tests/test_compaction_eval.py`.
- Gate: Tool and image cases shall retain required facts.

### H046. Select a measured summary model.

- Problem: A slow main model can increase compaction time.
- Files: `agent/context_compressor.py`, `agent/model_router.py`, and `agent/model_metadata.py`.
- Gate: The selected model shall meet fidelity and latency limits.

### H047. Separate cold and warm cache reports.

- Problem: The first request hides steady-state cache quality.
- Files: `run_agent.py`, `agent/conversation_loop.py`, and `agent/insights.py`.
- Gate: Reports shall show both buckets.

### H048. Centralize compaction metrics.

- Problem: Manual and automatic compaction paths can report different data.
- Files: `agent/context_engine.py`, `agent/context_compressor.py`, and `agent/insights.py`.
- Gate: Both paths shall use one metric source.

### H049. Preserve cache bytes after a stream retry.

- Problem: A dropped stream can reorder replayed tool results.
- Files: `agent/stream_single_writer.py` and `agent/conversation_loop.py`.
- Gate: A retry test shall preserve the stable prefix hash.

### H050. Add opt-in idle compaction.

- Problem: A large idle session can make the next short request slow.
- Files: `agent/context_compressor.py`, `gateway/run.py`, and `cli.py`.
- Gate: The task shall stop immediately when a new request arrives.

### Q051. Adapt anti-slop principles for Python.

- Problem: The TypeScript rules do not protect the Python core.
- Files: `pyproject.toml` and a new software development skill.
- Gate: New rules shall start in report-only mode.

### Q052. Enforce the existing ty configuration.

- Problem: Type checks do not run as a required gate.
- Files: `pyproject.toml` and `.github/workflows/`.
- Gate: Changed Python files shall pass `ty check`.

### Q053. Verify the generated skill manifest.

- Problem: Generated skill indexes can drift from source skills.
- Files: `scripts/build_skills_index.py` and a new manifest test.
- Gate: Regeneration shall produce no diff.

### Q054. Snapshot the tool registry deterministically.

- Problem: Duplicate plugin tools can hide registry changes.
- Files: `tools/registry.py` and plugin tests.
- Gate: The snapshot shall contain unique sorted tool names.

### Q055. Add a touched-file dead code gate.

- Problem: Unused code increases startup work and agent confusion.
- Files: `pyproject.toml` and a new dead code report script.
- Gate: New changes shall add no unused import or argument.

### Q056. Measure startup cold time.

- Problem: New imports can increase time to the first prompt.
- Files: `scripts/benchmark.py` and a new startup test.
- Gate: CI shall use a stable tolerance band.

### Q057. Add declared plugin capabilities.

- Problem: A plugin can register broad powers without disclosure.
- Files: `xavani_cli/plugins.py` and `xavani_cli/plugins_cmd.py`.
- Gate: An undeclared capability shall fail registration.

### Q058. Add plugin network policy.

- Problem: A plugin can open an unapproved network connection.
- Files: `agent/outbound_limiter.py` and plugin infrastructure.
- Gate: Unlisted destinations shall require explicit approval.

### Q059. Pin plugin versions and hashes.

- Problem: An upstream release can change plugin behavior silently.
- Files: `xavani_cli/plugins_cmd.py`, new `xavani_cli/plugin_lock.py`, new `tests/xavani_cli/test_plugin_lock.py`, and `~/.xavani/plugins.lock.json`.
- Gate: Install, upgrade, and rollback shall record exact hashes.

### Q060. Scan skill bodies before admission.

- Problem: A skill can contain prompt injection or unsafe scripts.
- Files: `agent/skill_preprocessing.py` and `tools/skills_guard.py`.
- Gate: A suspicious skill shall require confirmation.

### Q061. Add an adversarial prompt guard evaluation.

- Problem: Known patterns do not cover new injection forms.
- Files: `agent/prompt_guard.py` and `tests/adversarial/`.
- Gate: The evaluation shall track detection and false positives.

### Q062. Rate-limit gateway commands by platform.

- Problem: One channel can create expensive task storms.
- Files: `gateway/run.py` and `gateway/slash_access.py`.
- Gate: Limits shall not block trusted maintenance commands.

### Q063. Expire stale approvals.

- Problem: An old approval can authorize a changed command.
- Files: `tools/approval.py` and approval tests.
- Gate: The command hash and approval age shall both match.

### Q064. Add an optional file write sandbox.

- Problem: A plugin can write outside the active workspace.
- Files: `agent/file_safety.py` and file tools.
- Gate: An outside write shall require explicit approval.

### Q065. Add an outbound destination audit.

- Problem: Operators cannot inspect external destinations easily.
- Files: `agent/outbound_limiter.py` and `xavani_cli/doctor.py`.
- Gate: The audit shall list each destination and origin.

### Q066. Redact session exports.

- Problem: Exported transcripts can contain credentials.
- Files: `xavani_cli/session_export_md.py`, HTML export, CSV export, and `agent/redact.py`.
- Gate: A no-secrets mode shall fail on residual matches.

### Q067. Expand secret redaction patterns.

- Problem: JWT, PEM, and temporary cloud credentials can escape current patterns.
- Files: `agent/redact.py` and redaction tests.
- Gate: Property tests shall detect no residual secret.

### Q068. Audit safe log coverage.

- Problem: A module can log before the safe filter loads.
- Files: `xavani_cli/safe_logging.py` and logging tests.
- Gate: Representative logs shall contain no secret value.

### Q069. Add optional keyring storage.

- Problem: Local configuration can retain plaintext credentials.
- Files: `xavani_cli/config.py` and `xavani_cli/secrets_cli.py`.
- Gate: Headless environments shall retain a safe fallback.

### Q070. Prove the no-phone-home contract.

- Problem: The privacy promise lacks an automated network test.
- Files: `xavani.py`, `agent/outbound_limiter.py`, and a new privacy test.
- Gate: A representative offline session shall open no remote connection.

### Q071. Split `/btw` from `/background`.

- Problem: The current alias cannot provide a true side conversation.
- Files: `xavani_cli/commands.py`, `gateway/run.py`, and a new `agent/side_session.py`.
- Gate: `/btw` shall seed context and return a summary handoff.

### Q072. Show live side task progress.

- Problem: Operators cannot inspect active side or background work.
- Files: `tui_gateway/`, `cli.py`, and status components.
- Gate: The UI shall show task, elapsed time, and current tool.

### Q073. Add live skin reload.

- Problem: Theme development can require a process restart.
- Files: `xavani_cli/skin_engine.py` and skin tests.
- Gate: A changed skin shall apply within 1 second.

### Q074. Explain aliases in contextual help.

- Problem: Related commands can hide different execution semantics.
- Files: `xavani_cli/commands.py` and `xavani_cli/tips.py`.
- Gate: `/help btw` shall explain both side and background commands.

### Q075. Generate shell completions from the command registry.

- Problem: Completion files can drift from registered commands.
- Files: `xavani_cli/completion.py` and completion scripts.
- Gate: Generated completion names shall match the registry.

### Q076. Verify locale key parity.

- Problem: Locales can omit new command text.
- Files: `locales/` and a new parity test.
- Gate: Each locale shall declare all required keys.

### Q077. Add `/plugins doctor`.

- Problem: Plugin failures require manual log inspection.
- Files: `xavani_cli/plugins_cmd.py`, `xavani_cli/plugins.py`, and `xavani_cli/doctor.py`.
- Gate: The command shall remain read-only.

### Q078. Validate plugin manifests in CI.

- Problem: A manifest can claim missing hooks, commands, or skills.
- Files: `plugins/` and a new plugin manifest test.
- Gate: Each declared capability shall resolve at runtime.

### Q079. Add a plugin scaffolder.

- Problem: Plugin authors repeat fragile boilerplate.
- Files: `xavani_cli/scaffold.py` and `xavani_cli/templates/`.
- Gate: A generated plugin shall pass its generated test.

### Q080. Warn on plugin name shadowing.

- Problem: A user plugin can hide a bundled plugin silently.
- Files: `xavani_cli/plugins.py` and `xavani_cli/plugins_cmd.py`.
- Gate: The loader shall report each shadowed source.

### Q081. Enforce persona tool sets.

- Problem: A child persona can call an unrelated tool.
- Files: `xavani_cli/subagent_personas.py`, `agent/tool_executor.py`, and `tools/registry.py`.
- Gate: An unauthorized tool call shall fail with a clear reason.

### Q082. Fix delegated output schema enforcement.

- Problem: One child returned 59 items against a 50-item maximum.
- Files: `tools/delegate_tool.py` and `tests/tools/test_delegate.py`.
- Gate: Invalid final output shall trigger one correction and then fail.

### Q083. Enforce child file ownership.

- Problem: Isolated child contexts still share one mutable repository.
- Files: `tools/delegate_tool.py`, `agent/file_safety.py`, and delegate tests.
- Gate: A child shall not write outside its assigned paths.

### Q084. Redact child context and results.

- Problem: A child can receive or return unnecessary secret values.
- Files: `tools/delegate_tool.py` and `agent/redact.py`.
- Gate: Child logs and summaries shall contain no secret value.

### Q085. Harden timeout and stop propagation.

- Problem: A child can continue after the parent stops.
- Files: `tools/delegate_tool.py`, `agent/iteration_budget.py`, and process controls.
- Gate: A stop test shall leave no live child.

### Q086. Audit plugin entry points.

- Problem: Installed packages can register implicit plugins.
- Files: `xavani_cli/plugins.py` and `xavani_cli/plugins_cmd.py`.
- Gate: Strict mode shall load only approved entry points.

### Q087. Show plugin capabilities in status.

- Problem: Operators cannot see each plugin power quickly.
- Files: `xavani_cli/plugins_cmd.py` and status components.
- Gate: Each loaded plugin shall show tools, hooks, and network policy.

### Q088. Quarantine removed plugins.

- Problem: A plugin removal can destroy the last working version.
- Files: `xavani_cli/plugins_cmd.py` and uninstall logic.
- Gate: Restore shall recover the exact recorded hash.

### Q089. Confirm executable skills at first use.

- Problem: A new skill can execute code without clear admission.
- Files: `tools/skills_guard.py` and `agent/tool_guardrails.py`.
- Gate: A code-running skill shall require a trust decision.

### Q090. Improve skill search ranking and deduplication.

- Problem: Multiple sources can return the same skill.
- Files: `tools/skills_hub.py` and `xavani_cli/skills_hub.py`.
- Gate: Exact names shall rank before fuzzy matches.

### Q091. Record skill source and license.

- Problem: Vendored skills can lose upstream and license data.
- Files: `scripts/build_skills_index.py` and skill manifest tests.
- Gate: Trusted external skills shall include a source and license.

### Q092. Layer behavior rules below mandatory rules.

- Problem: Optional style packs can conflict with mandatory safety rules.
- Files: `agent/prompt_builder.py` and `xavani_cli/research_guidelines.py`.
- Gate: Mandatory rules shall win each conflict.

### Q093. Integrate Ponytail as an optional quality mode.

- Problem: Persistent Ponytail instructions can increase prompt size and conflict with mandatory rules.
- Files: The installed Ponytail plugin and Xavani plugin configuration.
- Gate: Builders use `full`. Reviewers use `review`. Other roles use `off`.

### Q094. Bound side-session context.

- Problem: An unbounded side thread removes the benefit of isolation.
- Files: `agent/side_session.py` and `agent/context_compressor.py`.
- Gate: The side thread shall enforce a hard token budget.

### Q095. Reuse a warm side session safely.

- Problem: Repeated side questions can rebuild the same context.
- Files: `agent/side_session.py` and `gateway/run.py`.
- Gate: A time limit and `/btw reset` shall remove stale state.

### Q096. Reap orphan side sessions.

- Problem: A process exit can lose an unfinished side result.
- Files: `agent/side_session.py`, `agent/followup_queue.py`, and shutdown logic.
- Gate: A shutdown test shall leave no child process.

### Q097. Fuzz prompt guard and message sanitation.

- Problem: Small text changes can bypass fixed detection patterns.
- Files: `agent/prompt_guard.py`, message sanitation, and `tests/adversarial/`.
- Gate: The corpus shall record detection and false positive rates.

### Q098. Add property tests for path, redaction, and sanitation.

- Problem: Security pure functions lack broad generated cases.
- Files: security modules and new property tests.
- Gate: The tests shall prove containment, redaction, and idempotence.

### Q099. Expand the CLI contract suite.

- Problem: New commands and aliases can dispatch incorrectly.
- Files: `tests/test_cli_contract.py` and command registry tests.
- Gate: Each registered command and alias shall have a contract case.

### Q100. Audit flaky test quarantine.

- Problem: Quarantined tests can remain unstable without ownership.
- Files: `tests/flakiness.json` and CI workflows.
- Gate: Each quarantined test shall have a reason, owner, and review date.

## 10. Rejected Subagent Proposals

The parent rejected these 9 proposals:

- Move the compaction summary after recent turns.
- Send adaptive cache keep-alive requests.
- Reuse the full main prefix in the summary request.
- Stream tool results while the model still generates.
- Store pending summaries inside the E103 state contract.
- Reuse mutable message objects to reduce local serialization.
- Share a provider cache prefix across isolated children.
- Omit unchanged payload blocks from stateless API requests.
- Send idle cache warm-up pings.

The proposals lack proof, duplicate another feature, or add unsafe behavior.

## 11. Execution Waves

### Wave 0. Complete E103.

Complete all 18 remaining E103 task headings.

Do not mix roadmap code with E103 code.

### Wave 1. Establish measurements.

Implement H001, H002, H005, H024, H025, H026, H027, H038, and H047.

Record the complete baseline before an optimization.

### Wave 2. Add security foundations.

Implement Q057 through Q070.

Audit all external sources before installation.

### Wave 3. Integrate external quality tools.

Install anti-slop skills in both agent environments.

Install Ponytail plugins in both agent environments.

Implement Q091, Q092, and Q093.

### Wave 4. Improve cache stability.

Implement H003, H004, H006, H012, H018, H030, H042, H043, H044, and H049.

Require before-and-after cache evidence.

### Wave 5. Improve compaction.

Implement H007 through H017, H028, H032, H045, H046, H048, and H050.

Keep each compaction change behind its own evaluation gate.

### Wave 6. Improve latency and throughput.

Implement H019 through H023, H031, H033 through H041, and Q056.

Measure before and after each change.

### Wave 7. Improve the worker harness.

Implement Q081 through Q090.

Use real failures from the 2026-08-15 worker batch as regression cases.

### Wave 8. Build the side channel.

Implement Q071, Q072, Q094, Q095, and Q096.

Use this dependency order: Q071, Q094, Q095, Q096, and Q072.

Keep `/background` unchanged.

### Wave 9. Improve code quality and developer tools.

Implement Q051 through Q055, Q073 through Q080, and Q097 through Q100.

### Wave 10. Run full integration gates.

Run the complete default suite once.

Run package, secret, privacy, and scope checks.

Run 3 independent review gates.

Request commit approval for each coherent change set.

## 12. Per-Feature TDD Contract

For each accepted feature:

1. Inspect the production path. Verify: read the implementation and all direct callers.
2. Write 1 failing test. Verify: the diff changes only the assigned test file.
3. Run only that test. Verify: the test fails for the intended behavior gap.
4. Confirm RED. Verify: no setup, syntax, or dependency failure causes RED.
5. Implement the minimum change. Verify: each changed line traces to the accepted feature.
6. Run the same test. Verify: the command exits with code `0`.
7. Confirm GREEN. Verify: the original behavior gap no longer appears.
8. Run the focused suite. Verify: the suite reports `0 failed`.
9. Run Ruff on changed Python files. Verify: Ruff reports `All checks passed!`.
10. Run ty on changed Python files. Verify: ty exits with code `0`.
11. Run a specification review. Verify: the verdict is `APPROVED` with no open issue.
12. Run a quality and security review. Verify: no P0 or P1 issue remains.
13. Run the integration gate. Verify: build, package, and focused integration checks pass.
14. Verify the final diff. Verify: the diff contains only approved paths.
15. Request commit approval. Verify: no path enters the staging area before approval.

Do not accept a setup failure as RED evidence.

Do not change a test expectation to make a weak implementation pass.

## 13. Review Gates

Gate 1 checks specification compliance.

Gate 2 checks simplicity, security, privacy, and maintainability.

Gate 3 checks build, tests, package, and integration evidence.

A fixer child may change code only after the parent accepts a finding.

The applicable reviewer shall review each correction again.

The parent shall verify all final claims directly.

## 14. Files That Shall Not Change During E103

Do not change these files during E103:

- `agent/conversation_loop.py`.
- `agent/context_compressor.py`.
- `agent/prompt_caching.py`.
- `tools/delegate_tool.py`.
- `xavani_cli/plugins.py`.
- `gateway/run.py`.
- `cli.py`.
- `pyproject.toml`.
- Any unrelated dirty path.

## 15. Risks and Tradeoffs

### Risk: A 100-item roadmap creates scope pressure.

Mitigation:

- Keep E103 first.
- Use one feature branch or approved commit group per coherent slice.
- Measure value before promotion.
- Reject features that duplicate current behavior.

### Risk: A cache target creates dishonest metrics.

Mitigation:

- Define the stable prefix denominator.
- Report raw and warm ratios separately.
- Record provider evidence.
- Do not guarantee an unsupported target.

### Risk: External plugins alter agent behavior.

Mitigation:

- Audit before install.
- Pin the source hash.
- Keep Ponytail off by default.
- Put mandatory safety rules first.
- Keep a rollback snapshot.

### Risk: The side channel conflicts with `/btw` history.

Mitigation:

- Preserve `/background`.
- Document the behavior change.
- Add CLI and gateway contract tests.
- Add `/btw reset`.

### Risk: Worker output appears valid but violates its schema.

Mitigation:

- Implement Q082 early in Wave 7.
- Require strict result validation.
- Treat malformed output as no verdict.
- Keep parent verification mandatory.

## 16. Open Decisions

Andile must confirm whether `150 seconds` means a maximum or a minimum.

The recommended target is a median task time of 150 seconds or less.

The parent recommends a runtime skill install for anti-slop.

The parent does not recommend an Oxlint install in the Python root.

The parent recommends a native Ponytail plugin install with global mode off.

## 17. Roadmap Validator Disposition

The assumption linter reports 3 findings.

All 3 findings inspect the home directory segment in an absolute macOS path.

The path segment does not identify an application actor.

The parent classifies all 3 findings as false positives.

The goal verifier reports `STRONG` with `54/75`.

The goal verifier recommends execution.

The feature audit reports these results:

- Feature count: `100`.
- Unique feature IDs: `100`.
- Missing IDs: `0`.
- Unexpected IDs: `0`.
- ID order: correct.
- Em dash count: `0`.

The independent quality reviewer returned `APPROVED` in delegation `deleg_556ff5ae`.

The reviewer reported these results:

- P0 issues: `0`.
- P1 issues: `0`.
- Feature count: `100`.
- Unique feature IDs: `100`.
- Invalid existing paths: `0`.
- E103 isolation: confirmed.
- The 99% cache denominator: confirmed.
- The 150-second ambiguity: confirmed.

The parent reviewed 3 P2 observations.

The parent corrected all 3 observations:

- H006, H014, H020, H043, and Q059 now name exact paths.
- Wave 8 now defines the side-session dependency order.
- H040 no longer depends on the unresolved 150-second value.

No open roadmap review issue remains.

## 18. Completion Criteria

The roadmap reaches completion only when:

- E103 has an approved plan.
- E103 completes all 18 remaining tasks.
- E103 has 3 approved review gates.
- The complete default suite reports 0 failures.
- All accepted updates have measured baselines.
- All accepted updates have focused tests.
- All changed Python files pass Ruff.
- All changed Python files pass ty.
- External sources have recorded hashes and licenses.
- Security scans report no unaccepted high issue.
- Privacy tests report no remote connection under the offline contract.
- Cache reports use the defined denominators.
- Performance claims include before-and-after evidence.
- No unrelated dirty path changes.
- No commit occurs without approval.

## 19. Execution Handoff

After user approval, resume the E103 plan at Task 3.

Use only paid DeepSeek V4 Flash subagents.

Keep the parent as the design lead and final authority.

Complete E103 before Wave 1.
