# R1 Integration Report

Date: 2026-09-14. Branch: `feat/r1-reliability`
(agent HEAD `62064f0f`; desktop HEAD `9918fd2`).

This artifact backs the claim "all tests pass together" for the R1 scope
(tasks 01-12, Addenda A/B, task 24). Every number below comes from a run on
the frozen commits above.

## C1 - Agent full suite (canonical runner, CI parity)

Command: `caffeinate -dims bash scripts/run_tests.sh` (4 workers, hermetic
env, `tests/integration` + `tests/e2e` excluded per the runner).

- Run 2 (certification): **19215 passed, 195 skipped, 0 failed, 358.14s**.
- Run 1: 19213 passed, 2 failed - both `tests/gateway/test_slack.py`
  thread-reply cases. Triage: nothing on the branch touches Slack code or
  its tests; both pass isolated (5/5) and file-level via the runner
  (186/186); run 2 green. Load/ordering flake class; logs preserved
  (`/tmp/r1-final-agent-run1-flake.log`, `/tmp/r1-final-agent-2.log`).

## C2 - Desktop suites

- `pytest -o addopts= -q tests/desktop` -> **203 passed** (auth, workspace
  boundary + adversarial corpus, revision saves, legal notices, commands).
- Node (per-file, `node --test`, 63 tests, 0 failures):
  security 19, workspace-grant 12, run-state 13, update-policy 8,
  adversarial-events 10, semver 1.
- Syntax: `node --check` on main/preload/security/workspace-grant/
  update-policy/run-state/app.js all OK; `bash -n scripts/build-macos.sh` OK.

## C3 - Cross-repo live smoke (engine from this branch)

Electron smoke with the dev harness (`XAVANI_DESKTOP_TEST`), engine
`~/xavani-agent`, backend via the stdin bootstrap secret:

- `[test] grant: {"ok":true,"root":"/private/tmp/xavani-ws-final"}` -
  native grant chain.
- `TREE-OK` - granted workspace tree rendered by the renderer
  (`xavani-ws-final` + `README.md`) through the authenticated injector.
- `CONSOLE-OK` - console WebSocket connected (authenticated handshake),
  working shell prompt `xavani>`.
- `errs: []` - no page errors. Screenshot (local):
  `/tmp/desktop-r1-final4.png`.
- Revision-conflict smoke (task 12 evidence): stale save -> 409 with disk
  preserved; correct revision -> 200; conflict view base/buffer/disk.

## C4 - Statement

"All tests pass together" holds as of the frozen commits above, with the
documented flake and the known residuals below.

## Known residuals (honest list)

- `image-size` -> `@docusaurus/*` chain: no fix exists upstream; tracked
  (see docs/reliability/security-wave.md).
- 45 CodeQL logging alerts: need dismissals (owner `security_events`
  scope) or the advanced-setup switch; config file is aligned either way.
- The desktop repository carries no root LICENSE (owner decision; flagged
  in its THIRD_PARTY_NOTICES.md).
- By-design LOW findings pinned by the adversarial corpus: approval binds
  to the pattern class; receipt store is host-trust-only; hashline drift
  warns without blocking.
- Run-1 flake class: Slack thread-reply tests under load (see C1).
- `bash 3.2` on the owner's machine required a runner fix
  (`26f29b56`); CI (bash 5) was unaffected.
