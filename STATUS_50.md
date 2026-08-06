# Xavani 50-Update Status Matrix
Date: 2026-08-06
Method: grep locate -> test evidence -> record. Items A01-A03, A05, A08-A10, B02-B03, B07-B08, C01-C02, C07-C08, D01, D08, E03-E05, F02-F03, F06, G03 are VERIFIED-PRESENT (code+test found in prior sessions) — list them as VERIFIED with their test file if you can find it quickly (one grep each, no test run).

| Item | Status | Implementation path | Test path | Evidence |
|------|--------|---------------------|-----------|----------|
| A04 | VERIFIED | agent/turn_finalizer.py, agent/turn_retry_state.py (finalize_turn + TurnRetryState, DEFAULT_MAX_RETRIES) | tests/agent/test_turn_finalizer.py | pytest: `6 passed in 1.34s` |
| A06 | VERIFIED | gateway/session.py SessionStore (mark_resume_pending/clear_resume_pending recovery, suspend_recently_active); xavani_state.py FTS v10 trigram backfill + v11 re-index rebuild (fixes #16751) | tests/test_xavani_state.py::TestFTS5ToolCallIndexing (-k FTS5), tests/gateway/test_clean_shutdown_marker.py | pytest: `26 passed in 1.75s` (FTS -k), `7 passed in 1.58s` (shutdown marker) |
| A07 | VERIFIED | gateway/run.py per-session lease: _running_agents sentinel (line 848), _running_agents_ts, stale-entry eviction (~6830-6865), _release_running_agent_state (14895) | tests/gateway/test_session_race_guard.py | pytest: `17 passed in 6.76s` |
| B01 | VERIFIED | agent/reasoning_timeouts.py max_reasoning_tokens_for(); enforced in agent/anthropic_adapter.py:2189 | tests/agent/test_reasoning_timeouts.py | pytest: `7 passed in 1.32s` |
| B04 | VERIFIED | agent/learn_prompt.py (module docstring: "B04: learn prompt pack (/learn)") | tests/agent/test_learn_prompt.py | pytest: `7 passed in 1.27s` |
| B05 | VERIFIED | xavani_memory/manager.py EpisodicMemory orchestration, summarize_session(), summarize_recent_episodes() (B05 marker at line 769), MEMORY.md promotion bullets | tests/xavani_memory/test_memory_summary.py | pytest: `5 passed in 1.15s` |
| B06 | VERIFIED | model_router.py suggest_reasoning_effort() (B06 marker at line 69), effort field on router result | tests/agent/test_reasoning_effort_auto.py | pytest: `6 passed in 1.31s` |
| C05 | VERIFIED | xavani_state.py apply_wal_with_fallback() (journal_mode=WAL -> DELETE fallback, lines 135-186), _try_wal_checkpoint() (457) | tests/test_xavani_state_wal_fallback.py | pytest: `15 passed in 1.53s` |
| G01 | VERIFIED | xavani_cli/notifications.py smart_notify(); gateway/run.py notification machinery (shutdown/restart/watch notifications, _send_restart_notification etc.) | tests/xavani_cli/test_notifications.py | pytest: `6 passed in 1.43s` |
| C06 | IMPLEMENTED | xavani_cli/main.py _acquire_update_lock()/_release_update_lock()/_update_lock_path() (fcntl.flock / msvcrt pattern, mirrors gateway/status.py), wired into cmd_update() (refuses when held, releases in finally) | tests/xavani_cli/test_update_lock.py | pytest: `4 passed in 1.46s` |
| C03 | IMPLEMENTED | xavani_cli/security_audit.py run_security_audit() (redact_secrets check + .env/config.yaml permission checks) + cmd_security_audit() report printer; `security-audit` subcommand registered in xavani_cli/main.py main() | tests/xavani_cli/test_security_audit_cmd.py | pytest: `7 passed in 1.45s` |
| C04 | IMPLEMENTED | xavani_cli/secrets_cli.py secrets_add()/secrets_list()/secrets_remove()/cmd_secrets() on ~/.xavani/.env (reuses config.save_env_value/remove_env_value/load_env; values never printed); `secrets add|list|remove` subcommands registered in xavani_cli/main.py main() | tests/xavani_cli/test_secrets_cli.py | pytest: `5 passed in 1.40s` |

## Batch 2 (2026-08-06)

| Item | Status | Implementation path | Test path | Evidence |
|------|--------|---------------------|-----------|----------|
| A04 | VERIFIED | agent/turn_finalizer.py, agent/turn_retry_state.py (finalize_turn + TurnRetryState, DEFAULT_MAX_RETRIES) | tests/agent/test_turn_finalizer.py | pytest: `6 passed in 1.34s` |
| A06 | VERIFIED | gateway/session.py SessionStore (mark_resume_pending/clear_resume_pending recovery, suspend_recently_active); xavani_state.py FTS v10 trigram backfill + v11 re-index rebuild (fixes #16751) | tests/test_xavani_state.py::TestFTS5ToolCallIndexing (-k FTS5), tests/gateway/test_clean_shutdown_marker.py | pytest: `26 passed in 1.75s` (FTS -k), `7 passed in 1.58s` (shutdown marker) |
| A07 | VERIFIED | gateway/run.py per-session lease: _running_agents sentinel (line 848), _running_agents_ts, stale-entry eviction (~6830-6865), _release_running_agent_state (14895) | tests/gateway/test_session_race_guard.py | pytest: `17 passed in 6.76s` |
| B01 | VERIFIED | agent/reasoning_timeouts.py max_reasoning_tokens_for(); enforced in agent/anthropic_adapter.py:2189 | tests/agent/test_reasoning_timeouts.py | pytest: `7 passed in 1.32s` |
| B04 | VERIFIED | agent/learn_prompt.py (module docstring: "B04: learn prompt pack (/learn)") | tests/agent/test_learn_prompt.py | pytest: `7 passed in 1.27s` |
| B05 | VERIFIED | xavani_memory/manager.py EpisodicMemory orchestration, summarize_session(), summarize_recent_episodes() (B05 marker at line 769), MEMORY.md promotion bullets | tests/xavani_memory/test_memory_summary.py | pytest: `5 passed in 1.15s` |
| B06 | VERIFIED | model_router.py suggest_reasoning_effort() (B06 marker at line 69), effort field on router result | tests/agent/test_reasoning_effort_auto.py | pytest: `6 passed in 1.31s` |
| C03 | IMPLEMENTED | xavani_cli/security_audit.py run_security_audit() (redact_secrets check + .env/config.yaml permission checks) + cmd_security_audit() report printer; `security-audit` subcommand registered in xavani_cli/main.py main() | tests/xavani_cli/test_security_audit_cmd.py | pytest: `7 passed in 1.45s` |
| C04 | IMPLEMENTED | xavani_cli/secrets_cli.py secrets_add()/secrets_list()/secrets_remove()/cmd_secrets() on ~/.xavani/.env (reuses config.save_env_value/remove_env_value/load_env; values never printed); `secrets add|list|remove` subcommands registered in xavani_cli/main.py main() | tests/xavani_cli/test_secrets_cli.py | pytest: `5 passed in 1.40s` |
| C05 | VERIFIED | xavani_state.py apply_wal_with_fallback() (journal_mode=WAL -> DELETE fallback, lines 135-186), _try_wal_checkpoint() (457) | tests/test_xavani_state_wal_fallback.py | pytest: `15 passed in 1.53s` |
| C06 | IMPLEMENTED | xavani_cli/main.py _acquire_update_lock()/_release_update_lock()/_update_lock_path() (fcntl.flock / msvcrt pattern, mirrors gateway/status.py), wired into cmd_update() (refuses when held, releases in finally) | tests/xavani_cli/test_update_lock.py | pytest: `4 passed in 1.46s` |
| G01 | VERIFIED | xavani_cli/notifications.py smart_notify(); gateway/run.py notification machinery (shutdown/restart/watch notifications, _send_restart_notification etc.) | tests/xavani_cli/test_notifications.py | pytest: `6 passed in 1.43s` |

Note: pre-existing failure unrelated to this batch — tests/xavani_cli/test_update_autostash.py::test_cmd_update_retries_optional_extras_individually_when_all_fails expects install commands WITHOUT `--upgrade`; commit 7c6a0ab (2026-08-06) added `--upgrade` to the update pipeline and the test was never updated. Verified via git log (test last touched at initial release eed43e4).


## Batch 3 (2026-08-06)

| Item | Status | Implementation path | Test path | Evidence |
|------|--------|---------------------|-----------|----------|
| D02 | VERIFIED | gateway/session.py _PII_SAFE_PLATFORMS (line 204) + PII stripping for non-safe platforms (285-292); redaction shared across gateway/platforms/ (helpers.py etc.) | tests/gateway/test_pii_redaction.py | pytest: `16 passed in 1.90s` |
| D03 | VERIFIED | tools/egress_policy.py EgressPolicy (allowlist + default-deny); tools/egress_enforcement.py EgressEnforcingTransport checks policy.check BEFORE socket opens (fail closed); maybe_enforce wired into client factory agent/agent_runtime_helpers.py:1287 | tests/tools/test_egress_enforcement.py | pytest: `7 passed in 1.59s` |
| D04 | VERIFIED | tools/tirith_security.py defaults tirith_enabled=True (line 88), tirith_fail_open=True (91); background install daemon (no inline blocking install) | tests/tools/test_tirith_security.py -k 'Disabled or FailOpen or ExitCodeMapping' | pytest: `10 passed in 1.67s` |
| D05 | VERIFIED | xavani_cli/doctor.py:1353 D05 marker — credential-file age check, warns when API-key files older than 90 days (rotation_days=90) | tests/xavani_cli/test_doctor.py -k rotation | pytest: `2 passed in 3.61s` |
| D06 | VERIFIED | tools/mutation_audit.py log_mutation (append-only JSONL, origin assistant_tool vs background_review, fail-open, no secrets); wired into memory_tool.py:586 (D06 marker) + skill_manager_tool.py:938 | tests/tools/test_mutation_audit.py | pytest: `7 passed in 1.56s` |
| E01 | VERIFIED | gateway/health.py (A10/E01 docstring) health_status/readiness_status state provider; xavani_observability/prometheus.py render_metrics_text + port resolution; wired into gateway/run.py:4024 (/metrics /health /ready endpoint) | tests/gateway/test_health_endpoint.py | pytest: `10 passed in 2.07s` |
| F01 | VERIFIED | acp_adapter/ auth.py + permissions.py + edit_approval.py + server.py + session.py; CI: tests.yml `test` job runs tests/ (full ACP matrix: manifest validity, tool round-trip, approval isolation) + core-gate 'Verify ACP version sync' step (tests.yml:221) | tests/acp/test_registry_manifest.py (+ 11 more tests/acp files) | pytest: `6 passed in 1.22s` |
| F05 | VERIFIED | .github/workflows/nix.yml — cachix-auth-token (line 34), FlakeHub Cache OIDC (line 11), nix flake check + nix build jobs | (workflow-only, no pytest) | grep evidence: `cachix-auth-token` + `nix flake check` + `nix build` in nix.yml |
| F04 | VERIFIED | scripts/install.ps1 — PortableGit download (509-612), Node 22 fallback (81/195/709), uv python install "no admin needed" (402), portable Git isolated from system (545) | tests/scripts/test_generate_installers.py + scripts/tests/test-install-ps1-stage-protocol.ps1 | pytest: `9 passed in 1.39s` |

## Batch 3 completion (2026-08-06, verified by Hermes directly after subagent timeout)

| Item | Status | Implementation path | Test path | Evidence |
|------|--------|---------------------|-----------|----------|
| D07 | IMPLEMENTED | tools/terminal_tool.py _git_capture/_repo_has_no_owner/_maybe_sandbox_untrusted_repo; wired into _get_env_config (ownerless git repo + TERMINAL_CWD -> docker sandbox, opt out XAVANI_UNTRUSTED_REPO_SANDBOX=0, fails open without docker) | tests/tools/test_terminal_sandbox_untrusted.py | pytest: `12 passed in 1.52s` |
| E02 | VERIFIED | agent/trajectory.py save_trajectory/record_turn_timeline/turn_timeline_path (per-turn trace export) | tests/agent/test_turn_timeline.py | pytest: `8 passed in 1.33s` (with test_flake_dashboard) |
| E06 | VERIFIED | tests/test_flake_dashboard.py load_entries/build_report (flakiness.json aggregation, ranking, top-N) | tests/test_flake_dashboard.py | pytest: `8 passed in 1.33s` (with test_turn_timeline) |
| G02 | VERIFIED | xavani_memory/manager.py build_daily_digest (G02 marker, line 782) | tests/xavani_memory/test_daily_digest.py | pytest: `3 passed in 1.02s` |
| G04 | VERIFIED | agent/followup_queue.py FollowUpQueue (line 37); wired into conversation_loop.py:4250 | tests/agent/test_followup_queue.py | pytest: `5 passed in 1.14s` |

## Complete 50-update matrix (all 26 tracked items have evidence)

VERIFIED: A04 A06 A07 B01 B04 B05 B06 C05 D02 D03 D04 D05 D06 E01 E02 E06 F01 F04 F05 G01 G02 G04
IMPLEMENTED: C03 C04 C06 D07
VERIFIED-PRESENT (prior sessions, listed in header): A01 A02 A03 A05 A08 A09 A10 B02 B03 B07 B08 C01 C02 C07 C08 D01 D08 E03 E04 E05 F02 F03 F06 G03

