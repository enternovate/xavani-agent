# SESSION HANDOFF — Xavani 0.3.0 build-out

Date: 2026-08-23. Author: ox-alpha session for Andile.
Plan of record: ~/.hermes/plans/20260823-100423-xavani-030-completeness.md
Prior handoff: planning/SESSION_HANDOFF_0.2.0.md

## STATE AT HANDOVER

Version 0.3.0 cut on BOTH repos (equal-version rule holds):
- Engine commits: 87ad55f, 5f2f251, 9ca92c5, 3fa5fb7, 080f456, 38f6f0b,
  d5b04fe (release bump). All conventional, explicit-path staging.
- Desktop commits: b9c087c, 24438ff, bf9ca28, e40a..., 6061a22 + settings,
  skills marketplace, import expansion, cron form.
- Browser extension vendored at ~/constellation-builds/xavani-browser-extension,
  branch xavani-rebrand, commit 8bd495f. Rebranded user-visible strings only
  (wire names stable); LICENSE dropped per owner instruction with upstream
  MIT attribution preserved in README NOTICE section. ESLint: 0 errors.

## RELEASE GATES (all green 2026-08-23)

- Engine full suite: 18462 passed, 269 skipped, 1 failed = known load-flake
  tests/xavani_cli/test_agent_hub.py::TestKill::test_kill_unknown_child_does_not_park
  (passes in isolation; verified 3 separate times this session).
- Desktop suite: passed. Parity: "parity OK: 91 commands" exit 0.
- Ruff clean on every touched file. node --check on app.js/main.js clean.
- Live verification: skills search/browse return real registry data;
  generate_document produced real pptx/xlsx/docx; preview brief route maps
  ops to file+line; todo routes round-trip through a live backend.

## KEY FACTS FOR NEXT SESSION

- tools/skills_hub.py is now REAL. Legacy stub-era skips (109) remain in
  tests/tools/test_skills_hub.py; unskip opportunistically.
- PersistentTodoStore: ~/.xavani/todos.json. OutstandingLedger:
  ~/.xavani/outstanding.jsonl. Both consumed by desktop routes
  /desktop/api/todos* and /desktop/api/outstanding.
- Slack slash clamp: new session-scoped CLI commands must either fit under
  the 50 cap or join _GATEWAY_EXCLUDED_COMMANDS (see /debug precedent).
- Shared-file hunk staging caught two foreign-hunk sweeps this session
  (cli.py commit ab7dd6e reverted and redone as 3fa5fb7; pyproject/xavani.py
  filtered before d5b04fe). Keep verifying staged diffs line-by-line.
- Delegation children hit the 600s ceiling on every large task this day;
  parent-side builds were faster and safer. Red-test/green-implement split
  across two children works when children are required.

## NOT YET DONE (next session candidates)

- git push both repos + tag v0.3.0 (needs enternovate account switch).
- macOS dmg build from clean tag export; Windows CI attaches on tag push.
- Website reference pages for /outstanding, /done, generate_document,
  preview_control.
- Extension: publish repo to enternovate org, Chrome Web Store listing.
