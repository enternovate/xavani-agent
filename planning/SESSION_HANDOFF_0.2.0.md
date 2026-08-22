# SESSION HANDOFF — Xavani 0.2.0 build-out

Date: 2026-08-22. Author: ox-alpha session for Andile.
Plan of record: planning/0.2.0-plan.md (500 items, 10 workstreams).

## HOW TO RESUME (next session)

1. Repo: /Users/andilemushwana/xavani-agent
   (remote: https://github.com/enternovate/xavani-agent.git)
2. Open this file and planning/0.2.0-plan.md first.
3. Opening prompt that works: "continue 0.2.0 plan from handoff".
4. Verify baseline before coding:
   python3 -m pytest tests/xavani_cli/test_loop_runner.py -q
   python3 -m scripts.task_bench.run_bench --faux
5. Work order: llm_judge verifier → watchdog loops via cron/jobs.py →
   gateway parity for /loop → advisor role → agent hub roster → atomic
   commit splitter → config importer → RPC mode → activity-formatter
   rollout across remaining commands → W6 packs → W7-W9 polish →
   version bump 0.2.0 + CHANGELOG LAST.
6. Rules that must survive every session: audit before building (much of
   W4/W5 already exists), filtered-hunk staging for shared files
   (cli.py, run_agent.py, agent/tool_executor.py carry other sessions'
   edits), ruff + targeted pytest + faux bench gates before every commit,
   extend _GATEWAY_EXCLUDED_COMMANDS when registry growth breaks Slack
   parity, conventional commits, never git add -A.


## State

12 commits on main (all gates green). Session 2 added:

13. 0df9ede agent hub roster (items 256-259): xavani_cli/agent_hub.py —
    /hub lists live children; steer via AIAgent.steer; kill interrupts
    one child + parks its goal; revive re-spawns via delegate_task.
    "hub" in _GATEWAY_EXCLUDED_COMMANDS. Tests:
    tests/xavani_cli/test_agent_hub.py.

11. 87e1b32 watchdog loops (items 47-48): xavani_cli/loop_watchdog.py
    tick runs ONE headless pass via `xavani -z`; /loop watch [every S]
    [passes N] [budget USD] [alert C] <prompt> creates spec + no-agent
    cron job in ~/.xavani/scripts/loop_watchdog_<id>.py; job silent
    while running, prints summary alert JSON on finish, removes its own
    cron job. Tick finalizes on stop conditions + runaway detection
    (post-pass re-check included). loop_runner.save() public wrapper.
    Tests: tests/xavani_cli/test_loop_watchdog.py.
- Gateway parity for /loop verified GREEN with no changes needed —
  /loop, /loops, /eval-loop already pass 143/143 registry tests
  (`python3 -m pytest tests/xavani_cli/test_commands.py -m integration`).
12. cb528b3 advisor reviewer role (items 252-255): xavani_cli/advisor.py
    (resolve_advisor_model, parse_notes cap 5, review_turn via
    auxiliary_client.call_llm, format_notes_block, never-raising
    maybe_review); hook at end of AIAgent.chat in run_agent.py;
    /advisor status|enable|disable in cli.py; "advisor" added to
    _GATEWAY_EXCLUDED_COMMANDS. Tests: tests/xavani_cli/test_advisor.py.

Older state: 10 commits through f849dba (write journal, /revert,
/permissions, batch approval, dry-run, model roles, loop engine,
baseline_tasks 20, verifier types, regression gate) plus shipped-since:
/eval, /eval-loop rubric, /loops prune, magic keywords, activity
formatter (wired into /loop /eval /eval-loop /loops), conflict resolver
core.

## Next steps after this handoff

- DONE since first handoff: /eval command (commit after 5704a0d) runs
  scripts/task_bench.run_bench.main in-session; supports --faux and
  --tasks <path>.
- /eval-loop SHIPPED: rubric-scored iterative refinement. Rubric file =
  contains:/regex: lines; load_rubric/rubric_score in loop_runner;
  /eval-loop <rubric-file> [threshold F] [passes N] <prompt>.
- /loops prune [days] SHIPPED: removes finished loop specs older than
  N days (default 7). loop_runner.prune + tests.
- Magic keywords SHIPPED: xavani_cli/magic_keywords.py detects
  ultrathink/orchestrate/workflowz in prose only (code spans, fences,
  tags, and path tokens excluded); AIAgent.chat expands them into turn
  directive notes. Items 260-263 done.
- Activity formatter SHIPPED (W7): xavani_cli/activity.py renders
  Hermes-style gutter lines (icon + verb + target + duration). Wired into
  /loop, /eval, /eval-loop. Remaining commands adopt it incrementally.
- Conflict resolver SHIPPED: xavani_cli/conflict_resolver.py parses
  conflict blocks incl. diff3 base sections; resolve_conflicts with
  ours/theirs/base; count_conflicts. Items 269-270 core done (CLI sugar
  /conflicts still to wire).
- llm_judge: verifier (needs model wiring; deferred deliberately).
- Watchdog loops via cron/jobs.py; gateway parity for /loop.
- W5 ports (checkpoint/rewind, memory tools retain/recall/reflect/learn,
  advisor role, magic keywords ultrathink/orchestrate/workflowz),
  W6 overlooked features, W7-W9 polish/docs/release.
- Version bump to 0.2.0 + CHANGELOG entry LAST.

## Audit findings (do NOT rebuild these)

Already present in 0.1.x, verified by code read on 2026-08-22:
- Dangerous-command approval system: tools/approval.py (1814 lines) — risk
  tiers, session/permanent allowlists, yolo, gateway prompts, timeouts,
  audit reasoning log.
- Fallback chains + cooldown restore: run_agent._fallback_chain,
  _try_activate_fallback, conversation_loop._restore_primary_runtime.
- Cache-hit telemetry: conversation_loop ~line 1789 prints cache hit %.
- Budget governor: agent/budget_governor.py. Cost meter: /cost handler
  cli.py:_show_cost. Per-call cost persistence: session DB
  update_token_counts in conversation_loop (~1745).
- Parallel tool execution: agent/tool_executor.py concurrent path;
  per-path file locks: file_state.lock_path.
- Hashline edits already exist: tools/edit_tool.py _apply_hashline.

## Git discipline used (keep doing this)

cli.py and agent/tool_executor.py carry OTHER sessions' unstaged edits.
Stage only own hunks: git diff <file>, filter hunks by content markers,
git apply --cached the filtered patch. Never git add -A.

## Next steps (in order)

DONE in session 2: watchdog loops + gateway parity verified + advisor
role + agent hub roster.

Next up: atomic commit splitter (266-268), config importer (271-272),
RPC mode NDJSON over stdio (276-277), llm_judge verifier (111 — the
advisor module shows the call_llm pattern to copy), checkpoint/rewind
(245-246) and memory tools retain/recall/reflect/learn (247-251),
activity-formatter rollout across remaining commands, W6 packs (331+),
W7-W9 polish/docs/release. Version bump 0.2.0 + CHANGELOG LAST.

Session-2 pitfalls: cli.py hunk positions SHIFT after every commit of
mine — always regenerate git diff and re-locate hunks by content before
git apply --cached. tools/delegate_tool.py carries another session's
edits — hub was built WITHOUT touching it (registry access only).

## Pitfalls learned today

- Slack 50-slash cap: EVERY registry addition can break
  TestSlackNativeSlashes::test_telegram_parity. Fix by extending
  _GATEWAY_EXCLUDED_COMMANDS (both platforms), never by touching tests.
  Check candidates against test pins first (codex-runtime is pinned).
- web_extract backend here is search-only; use curl raw.githubusercontent.com
  for external research.
- Delegate children time out at 600s on broad goals; keep child scope to
  one artifact.
