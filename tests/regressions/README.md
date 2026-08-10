# Regression Tests

Regression tests live in `tests/regressions/` and follow a strict,
issue-keyed convention (the "pi pattern"):

## Convention

- **One regression per file.** Each file encodes exactly one bug fix.
  Do not bundle multiple regressions into a single test module.
- **Naming:** `<issue-or-slug>-<short-description>.py`, e.g.
  `1234-fix-empty-model-fallback.py` or
  `ctx-halving-fix-wrong-session-dump.py`. Use the issue number when one
  exists; otherwise use a short lowercase slug.
- **Must fail on the buggy code and pass on the fix.** A regression test
  that passes before the fix is not a regression test — it is dead code.
  When you fix a bug, write the test against the broken behavior first
  (red), confirm it fails, then apply the fix and confirm it passes
  (green).
- **Self-contained:** each file imports only what it needs and can run in
  isolation: `python3 -m pytest tests/regressions/<file>.py -q`.
- **Keep the directory runnable as a suite:** files must not require
  network access, credentials, or a live LLM.

## Adding a regression

1. Pick the issue number or a short slug for the bug.
2. Create `tests/regressions/<issue-or-slug>-<short-description>.py`.
3. Verify it fails on the buggy code and passes on the fix.
4. Reference the issue/slug in a docstring at the top of the file.
