# SESSION HANDOFF — Xavani 0.2.0 build-out

Date: 2026-08-22 (end of day). Author: ox-alpha sessions 2-6 for Andile.
Plan of record: planning/0.2.0-plan.md (500 items).
Release notes: docs/release-notes-0.2.0.md

## HOW TO RESUME (next session)

1. Repo: /Users/andilemushwana/xavani-agent
   (remote: https://github.com/enternovate/xavani-agent.git)
2. Open this file and planning/0.2.0-plan.md first.
3. Opening prompt that works: "continue 0.2.0 plan from handoff".
4. Verify baseline before coding:
   python3 -m pytest tests/xavani_cli/test_commands.py -q -m integration
   python3 -m scripts.task_bench.run_bench --faux
5. Rules that must survive every session:
   - Audit before building — check what 0.1.x already covers first.
   - cli.py, agent/tool_executor.py, agent/skill_utils.py,
     tools/delegate_tool.py, tools/file_tools.py, xavani.py,
     pyproject.toml carry other sessions' edits. Stage ONLY your own
     hunks: git diff <file>, filter by content markers,
     git apply --cached. NEVER git add <shared-file> whole-file.
   - Hunk positions SHIFT after every commit — regenerate the diff and
     locate hunks by content each time.
   - Gates before every commit: ruff clean on touched files + targeted
     pytest + faux bench. Watch the FULL pytest output; a red test once
     slipped into an amend (fixed same-commit).
   - Registry additions tip Slack's 50-slash cap: add new desktop-only
     commands to _GATEWAY_EXCLUDED_COMMANDS (commands.py), never edit
     tests.
   - Delegation children were unreliable (1196s API timeouts, one wrote
     dead code) — build serially as parent; line-by-line verify any
     child artifact.
   - Conventional commits, --no-verify used by this workflow, never
     git add -A.

## STATE AT HANDOVER

Version 0.2.0 is cut: pyproject.toml, xavani.py VERSION, CHANGELOG entry
with migration notes, README What's New, release notes at
docs/release-notes-0.2.0.md. ~487/500 items done or audit-covered.
41+ commits since the original handoff commit f849dba.

Shipped by workstream (commit ranges in git log f849dba..HEAD):

- W1 approval gate: write journal, /revert [N], /permissions manager,
  batch approval preview, dry-run mode (sessions 1-2).
- W2 loop engine: loop_runner (stop conditions, reflexion notes,
  runaway/nested guards), watchdog loops via cron no_agent script jobs
  (/loop watch — silent ticks, alert on finish, self-removing job),
  eval loops with rubric scoring, /loops prune, activity formatter.
- W3 harness: baseline_tasks.json now 24 categorized tasks;
  verifiers jsonschema:/pytest:/exit_code:/llm_judge: (reasoning-model
  safe); per-task timeout_seconds; /eval --category/--runs/--save with
  config fingerprint; p95 + per-category medians; flake detection;
  regression_gate.py; leaderboard.py; authoring README; rubrics dir.
- W4 hardening: model roles (default/smol/slow/plan/advisor) +
  model.roles config keys. Fallback chains, parallel executor, cache
  telemetry, budget governor audited as pre-existing.
- W5 ports: advisor reviewer (/advisor, inline severity notes),
  agent hub (/hub list/steer/kill/revive), atomic commit splitter,
  conflict resolver, magic keywords, RPC mode NDJSON + tool cards,
  config importer, memory bank tools, read schemes pr:// issue://
  skill://, /fresh, director mode, /rewind checkpoints restore,
  turn-index fork /branch [name] at N. Hashline edits audited as
  pre-existing.
- W6 overlooked pack: staged writes wired into the live write path
  (/diff on|off toggles; /apply; /reject [seq]), /macro define/run/
  list/remove, handoff writer module, clipboard copy-last-code-block,
  transcript export module, cost dashboard module.
- W7 polish: xavani-terminal + xavani-ember skins, strict skin
  validation, doctor checks (permissions.json, loops, bench results),
  help-text audit codified as tests (5 weak args_hints fixed).
- W8 packs: 8 workflow packs under oag_skills/workflow-packs/ (189
  skills indexed) + PACKS.md index + pack-derived bench tasks.
- W9 release: CHANGELOG 0.2.0, version bump, migration notes, README
  section, installers pre-create loops/macros/scripts/memories-bank,
  website reference pages (permission-modes, loops, eval-harness,
  model-roles).

## REMAINING OPEN (all external blockers — item numbers in plan)

1. llm_judge live YES/NO confirmation: code fixed + unit-tested; the
   confirming run hit provider CreditsError. Owner tops up OpenRouter
   credit, then:
   XAVANI_BENCH_JUDGE_MODEL=<model> python3 -m scripts.task_bench.run_bench /tmp/judge_task.json
2. Website screenshots (owner, needs running app).
3. Tagged GitHub release + push (owner step).
4. Optional enforcement-side wiring IF agent/skill_utils.py or
   agent/tool_executor.py ever go clean of concurrent edits:
   skill-trigger discovery hook; nothing else pending.

## KEY FILE MAP (this build-out)

- Loop engine: xavani_cli/loop_runner.py, loop_watchdog.py
- Advisor/hub/director: xavani_cli/advisor.py, agent_hub.py, director.py
- Workflow: commit_splitter.py, config_importer.py, macros.py,
  memory_tools.py, handoff_writer.py, transcript_export.py,
  clip_code.py, cost_dashboard.py, staged_changes.py,
  read_schemes.py, rpc_mode.py, skill_triggers.py
- Harness: scripts/task_bench/{run_bench,leaderboard,regression_gate}.py,
  tasks/baseline_tasks.json (24), rubrics/, README.md
- Hooks into shared files: AIAgent.chat advisor hook (run_agent.py);
  delegate_tool.py one guarded director-filter hunk; file_tools.py
  staged-write hook after dry-run check; skin validation call in
  cli.py /skin handler.

## PITFALLS LEDGER (survive every session)

- Whole-file `git add` on shared files published another session's
  hunks once (caught, soft-reset, redone filtered). Never again.
- web_extract backend here is search-only; use curl raw.githubusercontent.com
  for external research.
- Broad child goals time out; delegation backend itself failed this
  day — serial parent builds preferred.
- Reasoning models need max_tokens headroom and reasoning-text fallback
  when parsing judge verdicts.
- tests/xavani_cli/test_commands.py runs at integration tier:
  pytest -m integration or it silently collects nothing.
