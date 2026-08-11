# Nightly Channel (H190)

The nightly channel is a daily full-suite validation with a promotion
path. It follows the Cap `promote-nightly.yml` pattern: a nightly build
promotes to a versioned tag only when the suite is green.

## What runs

- Every day at 02:00 UTC (`.github/workflows/nightly.yml`).
- Full venv suite on Ubuntu, same command as the `Tests` workflow.
- The run is non-blocking: a red suite is reported but does not abort
  the pipeline.
- The `promote` job reads the suite summary and refuses to tag when the
  suite shows failures.

## What promotes

`scripts/promote_nightly.py` creates an annotated tag:

```
nightly-<version>-<YYYYMMDD>
```

Preflight checks (all must pass):

1. The suite summary JSON shows zero failures and at least 1 pass.
2. `CHANGELOG.md` contains an entry for the current pyproject version.
3. No nightly tag already exists for that version.

Dry-run is the default:

```bash
python3 scripts/promote_nightly.py --summary artifacts/summary.json
```

Create the tag:

```bash
python3 scripts/promote_nightly.py --summary artifacts/summary.json --execute
```

## Manual promote

Dispatch the `Nightly` workflow manually (Actions -> Nightly -> Run
workflow). The `promote` job only runs on the schedule, so a manual
dispatch validates the suite without tagging. To tag manually, run the
script locally and push:

```bash
python3 scripts/promote_nightly.py --summary artifacts/summary.json --execute
git push origin "$(git tag --list 'nightly-*' | tail -1)"
```

## Stability rule

The `stable` release process stays manual. Nightly tags are evidence:
they show a version that passed the full suite. Promotion to `stable`
still requires a human release decision.
