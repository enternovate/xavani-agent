# Xavani Edge Report — Upstream Parity Ports

Date: 2026-09-06. Head: see git log. Plan: the 2026-09-04 parity plan (session archive).

Method: every slice follows TDD (RED new tests fail, GREEN pass), ruff clean,
case-blind brand grep, 1 commit per slice. Figures below come from real tool
output, not estimates.

## Totals

- Port test files: 131 files under tests/.
- Commits in repo: 511+ (parity chain starts 483d8a1).
- Full suite: see Suite section below.
- Brand rule: zero upstream-brand code hits in ported files. The internal
  provider key stays only as inert plumbing for stored logins. The
  `synchronous` substring hits are false positives.

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
cli_commands_mixin, slash_exec, pets, portal_cli,
container_boot, journey (merged with native), browser probe helpers,
managed_uv, model_catalog, macos_tcc_anchor, _scan_venv_blockers,
update_cmd epic (11354 lines).

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

- The upstream diagnostics-upload module: vendor-internal S3 phone-home.
  Xavani ships zero phone-home by design. Never port.
- The upstream subscription module (1482 lines): Xavani owns a native
  implementation (803 lines, Enternovate header, zero upstream hits,
  rewired to Xavani auth/config/gateway).
  Owner decision 2026-09-06: never port the upstream version over it.
  portal_cli guards resolve against the native module.
- agent/pet/generate/: dev-time sprite tooling, no runtime imports.

## Enternovate rebrand (2026-09-07, commit 44305506)

Owner rule: nothing leads to upstream vendors; everything falls under
Xavani agent plus Enternovate. 70 files changed, ruff clean,
targeted tests green.

- URLs: portal/inference/docs hosts now enternovate.co.za,
  xavani-agent.enternovate.com, inference-api.enternovate.co.za.
  Plugin index default now enternovate.co.za/xavani-agent/plugins.
  ASSUMPTION for owner to confirm: portal.enternovate.co.za and
  inference-api.enternovate.co.za must exist or be replaced with the
  real Enternovate service hosts.
- Env: XAVANI_* primaries everywhere; legacy vendor env vars kept as
  read fallbacks so existing logins keep working.
- Strings: vendor portal/login/model/credits/subscription wording now
  Xavani/Enternovate in all user-facing text.
- Removed: the vendor debug flag and its private-upload path (dead flag;
  uploads always used pastebin). Zero phone-home holds.
- Kept by design: the internal provider key (dict keys, auth state,
  function names). Renaming breaks stored logins; it is invisible.

## Remaining gaps (evidence, not guesses)

- The upstream Windows gateway module (1959 lines): watcher import
  guarded. Needs its own slice.
- The upstream proxy CLI module (903 lines) plus the proxy sources
  package: slash_exec egress guarded. Needs its own slice.
- Upstream keeps decomposing god-files (Sep 2026 facade pattern):
  auth_* (13 files), cli_*_mixin (8 files), state_* (17 files).
  Xavani covers these AREAS natively in its
  monoliths (cli.py 16161 lines, auth.py 7478 lines with 100+ hits per
  provider family, xavani_state.py 3857 lines). File absence is
  architecture difference, not proven feature absence. Per-area diffs
  remain future work.
- Upstream hash drift: runtime 13e72fb2 vs known 63279301 (Slice D).

## Agent-only endpoints (2026-09-07, commit 58693198)

Owner: Xavani ships the agent, not inference/portal services. No
Enternovate service hosts exist, so portal/inference URL defaults are
empty strings. Portal commands fail closed with clear messages.
Portal fetchers were already fail-open. The provider key stays as
inert plumbing for stored logins; no traffic can reach any vendor (no
URLs remain) and no Enternovate hosts are invented.
- Login page brand reads Xavani Agent.
- The vendor debug flag's private-upload path deleted (was a dead flag).
- web_dist bundle still embeds old strings: generated artifact,
  refreshes on next frontend rebuild. Never hand-edited.
- Kept: MIT attribution (LICENSE/README/AGENTS.md), identity
  disclaimers, data-compat keys, and the scrub guard.

## Subscription scrapped (2026-09-07, commit 79d9f415)

Owner: no subscription product exists. Deleted 7 subscription/billing
modules plus 4 port tests, 6039 lines removed. Subscription prompt
returns "". Portal tools/status fail closed. Setup/tools/status run
direct paths via an inert features helper. 461 unit plus 122 integration
tests green on touched files.

## Suite

Full `pytest tests/` (2026-09-07, HEAD 3ef6b8ed): 18880 passed,
269 skipped, 0 failed in 348s. Every slice commit also shows its own
GREEN run (new tests plus prior port files, ruff clean).
