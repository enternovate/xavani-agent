# Xavani Edge Report — Hermes Parity Ports

Date: 2026-09-06. Head: see git log. Plan: .hermes/plans/2026-09-04_162315-xavani-hermes-parity.md.

Method: every slice follows TDD (RED new tests fail, GREEN pass), ruff clean,
case-blind brand grep, 1 commit per slice. Figures below come from real tool
output, not estimates.

## Totals

- Port test files: 131 files under tests/.
- Commits in repo: 511+ (parity chain starts 483d8a1).
- Full suite: see Suite section below.
- Brand rule: zero `hermes` code hits in ported files. `nous` stays only for
  the external Nous vendor (provider id, Portal URLs, token names), matching
  Xavani auth truth. `synchronous` substring hits are false positives.

## Ported (functional, tested)

CLI layer: _early_recovery, _install_repair, _startup_fast, approval_mode,
active_sessions, input_sanitize, gitlock, archive_safe, focus_view,
fallback_config, heartbeat, foreign_sessions, approval_transport,
approvals_test, approvals_suggest, context_switch_guard, image_provenance,
init_command, doctor_live, credential_lifecycle, build_info, agent_plugins,
lifecycle, memory_oauth, install_identity, mcp_catalog, mcp_picker,
mcp_startup, bang_shell, blueprint_cmd, agent_import, kanban_transfer,
provider_catalog, partial_compress, loops, session_export (+html native kept),
session_listing, setup_hidden_env, skin_cmd, session_lost_and_found,
session_recovery, sessions_cmd, suggestions_cmd, terminal_notify,
urllib_security, resource_limits, terminal_breadcrumbs, update_lock,
update_receipt, update_contract, update_inventory, worktree_cmd, worktree_gc,
security_audit_startup, update_restart_recovery, update_abort_recovery,
web_git, web_models, web_deps, pty_session, psutil_android,
relay_plugin_cutover, linux_desktop_entry, setup_whatsapp_cloud,
dashboard_procs, dashboard_register, sse_done, win_pty_bridge,
windows_ssh_runtime, subcommands package (46 files), console_engine,
dashboard_auth package (13 files), cli_agent_setup_mixin,
cli_commands_mixin, cli_billing_mixin, slash_exec, pets, portal_cli,
container_boot, journey (merged with native), browser probe helpers,
managed_uv, model_catalog, macos_tcc_anchor, _scan_venv_blockers,
update_cmd epic (11354 lines), nous_account, nous_billing.

Agent layer: turn_context, message_metadata, skill invocation block,
merged markers, FTS error classes, repair classifiers, turn-context chain
(billing_view, billing_usage, subscription_view, anchored tokens, trivial
prompt, compaction status, compression recovery chain).

State layer: xavani_state_common (1391), repair probe chain
(_db_opens_cleanly and helpers), xavani_state_wal, xavani_state_repair
(full strategies), xavani_state_holders, tombstone helpers, transcript
limits, FTS availability classifier, constants update chain
(venv_python_path, node dirs, first-party roots, partial-update hint).

Helpers merged into existing files: models cache, mcp bearer auth,
noninteractive git env, mcps dir, split_command_line, harden_git_argv,
line_input, bounded_probe_run, rearm_oneshot (adapted, no claim
subsystem), home rewrite + allowlist approval helpers, portable MCP probe.

## Adapted, not copied

- console_engine _sessions_repair guards the repair import (landed later).
- _cron_resume rearm drops claim checks (no claim subsystem in Xavani).
- anchored_context_tokens calls the Xavani estimator without the kwarg.
- _live_writer_holds_db probes directly (no holders scan at the time;
  holders module ported later).
- report_startup_progress guarded (no watchdog module in Xavani).
- journey.py merges ported timeline with native dispatch names
  (cmd_journey, build_journey_parser, _fmt_graph).
- model_catalog.py keeps the ported full file plus the native log header.
- update_cmd guards 53 missing names (gateway launchd set, backup set,
  profiles backfill since ported; full list in commit 777e0de1 notes).

## Deliberately skipped

- hermes_cli/diagnostics_upload.py: Nous-internal S3 phone-home. Xavani
  ships zero phone-home by design. Never port.
- agent/pet/generate/: dev-time sprite tooling, no runtime imports.

## Remaining gaps (evidence, not guesses)

- hermes_cli/nous_subscription.py (1482 lines): portal_cli and account
  paths guard it. Needs its own slice.
- hermes_cli/gateway_windows.py (1959 lines): watcher import guarded.
  Needs its own slice.
- hermes_cli/proxy_cli.py (903 lines) + agent/proxy_sources/iron_proxy:
  slash_exec egress guarded. Needs its own slice.
- Upstream keeps decomposing god-files (Sep 2026 facade pattern):
  hermes_cli/auth_* (13 files), hermes_cli/cli_*_mixin (8 files),
  hermes_state_* (17 files). Xavani covers these AREAS natively in its
  monoliths (cli.py 16161 lines, auth.py 7478 lines with 100+ hits per
  provider family, xavani_state.py 3857 lines). File absence is
  architecture difference, not proven feature absence. Per-area diffs
  remain future work.
- Upstream hash drift: runtime 13e72fb2 vs known 63279301 (Slice D).

## Suite

Full `pytest tests/` (2026-09-06, HEAD 8da3c1af): 18896 passed,
269 skipped, 0 failed in 521s. Every slice commit also shows its own
GREEN run (new tests plus prior port files, ruff clean).
