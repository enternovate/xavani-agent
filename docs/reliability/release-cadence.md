# Release cadence — recurring process (task 27)

## Policy

- Each week: review upstream security and reliability changes
  (`upstream-review.md`).
- Each accepted fix: run the smallest relevant regression cases.
- Each release candidate: run the full release checklist
  (`release-checklist.md`, task 26).
- Each stable release: obtain owner approval first.

No cron jobs run without separate approval.
No publication happens without explicit publication approval.
Release frequency is not a quality signal.

## CI change filters

Each change class runs the smallest test set that covers it:

- JavaScript-only change (desktop `src/**`, renderer, preload): desktop
  JavaScript tests (`cli-parity.yml`, `js-tests` job).
- Desktop backend-only change (`backend/**`): desktop backend tests
  (`cli-parity.yml`, `backend-tests` job).
- Shared protocol change (command snapshot, `scripts/check_parity.sh`,
  engine command registry): both repositories' contract tests
  (`cli-parity.yml`, `parity` job; the agent `tests.yml` suite).
- Agent evaluation surfaces (`scripts/task_bench/**`, the bench test
  files): the bench faux gates (`eval-gate.yml`).

Placement:

- The desktop workflows run on every desktop pull request; the weekly
  schedule checks command parity.
- The agent eval gate runs on pull requests that touch steer paths, the
  golden evals, and the evaluation surfaces.
- The nightly suite runs the full agent test path plus the bench faux
  gates (non-blocking; the promote gate reads the suite summary).

## Version policy

- Do not introduce new version names. Keep the current version (0.3.0)
  and update the existing release and artifacts in place.
- The owner names any version change explicitly.

## Checklist

The full release checklist lives in `release-checklist.md` (task 26).
