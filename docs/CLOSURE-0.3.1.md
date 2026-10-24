# Closure record — 0.3.1

Date: 2026-10-24
Engine: `enternovate/xavani-agent`, branch `release/0.3.1-closure`, base `fe3a8121`
Desktop: `enternovate/xavani-desktop`, branch `release/0.3.1-closure`, base `1a478c75`

## 1. Scope

This record closes the 0.3.x cycle. It covers two repositories, 15 engine commits, 8 desktop commits, 25 Dependabot pull requests, 3 open issues, 5 plan documents, and every open dependency advisory that has a published fix.

## 2. Branch disposition

| Branch | Disposition |
| --- | --- |
| `main` | Trunk. Receives the closure merge. |
| `release/0.3.1-closure` | Merge branch. Deleted after the merge. |
| `feat/omera-api-mode` | Merged into `main` through the closure branch. Deleted. |
| `feat/r1-reliability` | Already contained in `feat/omera-api-mode`. Deleted. |
| `backup/feat-omera-api-mode-prepush-49307c97` | Content confirmed pushed. Deleted. |
| `dependabot/*` | Merged or closed by the Dependabot sweep. Branches without an open pull request deleted. |

## 3. Pull request disposition

| PR | Disposition |
| --- | --- |
| `#118` R1 reliability | Closed as superseded. Every commit is contained in the closure branch. |
| desktop `#1` | Closed as superseded by the desktop closure pull request. |
| 25 Dependabot pull requests | Merged when the checks are green. Closed when the bump is superseded by a later pin. |

## 4. Issue disposition

| Issue | Fix |
| --- | --- |
| `#141` portal detection | `8aad5ca3` adds `is_portal_base_url` and replaces 3 substring checks. |
| `#142` dead upstream URL | `475cb963` points the systemd unit at the live docs URL. The `README.zh-CN.md` links were already clean. |
| `#143` missing kanban PDF | `f00292af` replaces 10 references in 6 files with the live user guide. |

## 5. Plan disposition

| Plan | Disposition |
| --- | --- |
| `.hermes/plans/2026-08-13_162744-e103-durable-state-quality-control.md` | CLOSED-EXECUTED. The plan's own verifier reported `STRONG`, 34 of 42. Archived. |
| `.hermes/plans/2026-08-15_102746-xavani-agent-revolution-roadmap.md` | CLOSED-SUPERSEDED by `planning/reliability-master-plan.md`. Archived. |
| `.hermes/plans/2026-09-04_162315-xavani-hermes-parity.md` | CLOSED-EXECUTED. `docs/reliability/parity-report.md` records the ports. Archived. |
| `planning/0.2.0-plan.md` | CLOSED-EXECUTED. 0.2.0 shipped. Archived. |
| `planning/reliability-master-plan.md` | KEPT. Tasks 1 to 24 and 27 are delivered. Task 25 is decided below. Task 26 gained the manifest checker, the build guard, and the checklist. |

All 4 archived plans carry a CLOSED header that names this record.

The roadmap holds 50 items. Every item names files that exist in the tree. File presence is not delivery evidence, so no roadmap item is claimed as shipped here. The 50 items stay CARRIED, listed in the archived plan. The reliability master plan owns the delivered reliability work.

## 6. CI repairs

| Defect | Fix | Evidence |
| --- | --- | --- |
| `nightly.yml` pinned an unresolvable artifact action | The pin now matches the 3 other workflows | `nightly` run after the merge |
| Skills-index watchdog crashed on an empty published body | `scripts/check_skills_index_freshness.py` treats an unreadable or non-JSON index as `PENDING-DEPLOYMENT` | 3 unit tests; local run prints `PENDING-DEPLOYMENT` or `FRESH` |
| The watchdog pointed at a host that 404s the index path | It now reads the Pages artifact first, then the public host | Local run reads the Pages copy |
| Version drift: `xavani_cli.__version__` was `0.1.2` | It reports `0.3.0`; `tests/scripts/test_version_lockstep.py` locks the 3 version fields | 1 passed |
| Desktop backend tests died during collection | The engine root is resolved at import but a missing engine is no longer fatal; the CI job checks out the engine and sets `XAVANI_ENGINE_ROOT` | 204 desktop tests pass locally |
| Nix npm hash went stale after the dependency refresh | `fix(nix): refresh npm lockfile hashes` (`e51a901c`) | nix workflow re-runs on the closure head |

Known limitation: `.github/workflows/tests.yml` sets `continue-on-error: true` on the main `test` job. A green pull request does not prove the suite passes. The local canonical run is the proof.

## 7. Vulnerabilities

`npm audit`:

| Package | Before | After | Runtime after |
| --- | --- | --- | --- |
| `scripts/whatsapp-bridge` | 4 total, 1 critical | 0 | 0 |
| `web` | 6 total, 4 high | 0 | 0 |
| `website` | 48 total, 19 critical | 0 | 0 |
| `ui-tui` | 8 total, 6 high | 3 high, dev only | 0 |

`pip-audit` on the exported lock: 19 advisories before, `No known vulnerabilities found` after. Bumped: `pyjwt` 2.13.0 to 2.15.0, `urllib3` 2.7.0 to 2.8.0, `certifi` 2026.6.17 to 2026.10.23.

Desktop: 2 advisories (1 critical) to 0. `dompurify` moved to 3.4.17. The nested copy under `monaco-editor` is pinned through an override. The vendored bundle and `THIRD_PARTY_NOTICES.md` were refreshed to match.

Residual:

- `ui-tui`: `zod`, `zod-validation-error`, and `eslint-plugin-react-compiler` are dev-only. No non-breaking fix exists. A zod 3 to 4 migration is a separate task.
- CodeQL: the token lacks `security_events`, so the alert list cannot be read. Owner action.

## 8. Reliability plan status

| Task group | Status |
| --- | --- |
| Tasks 1 to 12 | Delivered before this cycle. |
| Tasks 13 to 24 | Delivered, reviewed in `docs/reliability/review-r2-r3.md`. |
| Task 25, real-model matrix | See the decision below. |
| Task 26, package from evidence | Manifest checker, build guard, and checklist delivered. A signed public candidate needs owner credentials. |
| Task 27, recurring release | Delivered: `upstream-review.md`, `release-cadence.md`, CI change filters. |

Task 25 decision: the owner accepted the 2-of-9 partial matrix on 2026-10-24. The report keeps its measured numbers and drops the billing blocker from the status line.

### Test evidence

Canonical runner: `XAVANI_TEST_WORKERS=4 bash scripts/run_tests.sh -q`.

| Run | Result |
| --- | --- |
| 1 | 19530 passed, 8 failed, 195 skipped, 7m54s |
| 2, after the search-envelope test fix | 19533 passed, 5 failed, 195 skipped, 7m41s |

Run 2 failures:

- `tests/xavani_cli/test_opencode_go_flat_namespace.py::test_deepseek_v4_flash_stays_on_opencode_go` — pre-existing. The catalog returns `deepseek-v4.1-flash` for the bare name. `xavani_cli/model_catalog.py` last changed on 2026-09-07, before this branch. No closure commit touches it.
- `tests/tools/test_delegate.py::TestDelegateHeartbeat::test_heartbeat_does_not_trip_idle_stale_while_inside_tool` — pre-existing timing budget. It expects more than 6 heartbeat touches in 0.4s at a 0.05s interval. `tools/` last changed on 2026-09-14. No closure commit touches it.
- `tests/gateway/test_memory_monitor.py::test_periodic_timer_fires`, `tests/cli/test_help_context.py::test_idle_state_shows_chat_basics_only`, and `tests/gateway/test_tool_event_identity.py::TestEnvelopeOnLiveRunStream::test_every_streamed_event_carries_the_run_envelope` — load-sensitive. All 3 pass in isolation (21 passed).

Targeted suites, all green:

- `tests/omera`: 77 passed.
- `tests/agent`: 3473 passed, 3 skipped.
- `tests/scripts` version and freshness guards: 4 passed.
- `tests/docs/test_docs_index.py`: 2 passed.
- `tests/test_portal_detection.py`: 7 passed.
- Kanban integration: 321 passed, 1 skipped.
- Ruff on every changed file: `All checks passed!`
- `uv lock --check`: clean.

Desktop:

- Backend suite: 204 passed.
- `npm run test:unit`: 106 passed.
- `npm run check:syntax`: exit 0.
- `npm run test:e2e`: 27 to 29 of 30 specs pass across attempts. The failure reproduces on the base commit. CI does not run these specs.


## 9. Residual risks

- The CI `test` job is non-blocking by design. Local runs are the only full-suite evidence.
- Desktop end-to-end tests are environment-sensitive on this machine. A run of `npx playwright test` produced 27 to 29 passing specs out of 30 across attempts. The same failure reproduces on the unmodified base commit, so it is not a regression from this closure. CI does not run these specs.
- `ui-tui` dev-only advisories stay open by decision.
- `web_dist` is gitignored but tracked. The dashboard bundle is committed because packaging reads that directory.
- The website depends on two exact overrides (`tinypool`, `postcss-selector-parser`). A future Docusaurus major may drop them.
- The roadmap's 50 items are untriaged beyond file presence.
- Two pre-existing engine test failures stay open: the opencode-go model alias assertion and the delegate heartbeat timing budget. Both predate this branch and no closure commit touches their source. They need their own fix.

## 10. Owner actions

1. CodeQL: run `gh auth refresh -h github.com -s security_events`, then read or dismiss the alerts. Or switch the repository to advanced setup, which the repo already configures in `.github/codeql/codeql-config.yml`.
2. Task 25: fund the OpenModel gateway, or accept the partial matrix.
3. Vercel edge host: run `vercel link` and `vercel --prod` in `deploy/vercel-edge`, then check the 401.
4. Signing: provide the Apple and Windows identities before any public candidate.
5. Release: approve the tag and the notes.

## 11. Repository organisation

| Move | From | To |
| --- | --- | --- |
| Parity report | `XAVANI_EDGE_REPORT.md` | `docs/reliability/parity-report.md` |
| Docs index | none | `docs/README.md`, guarded by `tests/docs/test_docs_index.py` |
| Planning index | none | `planning/README.md` |
| Closed plans | `planning/` and `.hermes/plans/` | `planning/archive/` |
| Omera docs | none | `website/docs/user-guide/features/omera-api.md`, listed in the sidebar |
| Kanban docs | unlisted page | Added to the sidebar |
| Debris | `MagicMock/`, root `__pycache__/`, 3 prunable worktrees | removed |
| Omera deploy pins | `fastapi==0.115.14`, `uvicorn==0.30.6` | `0.133.1` and `0.41.0`, matching the `web` extra |
