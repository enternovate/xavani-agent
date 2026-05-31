---
name: ship-it-preflight
description: Pre-release checklist — verify all gates pass before shipping code to production.
categories:
  - software-development
  - devops
platforms:
  - all
tags:
  - release
  - checklist
  - quality
condition: Before any release, deploy, or merge to main.
---

# Ship-It Preflight Checklist

> "If it isn't tested, it isn't done. If it isn't monitored, it isn't shipped."

## When to use

- Before merging a PR to main.
- Before deploying to production.
- Before releasing a new version.

## Prerequisites

- All tests pass locally.
- Code has been reviewed (by self or peer).

## Steps

### 1. Tests

```bash
# Run the full test suite
pytest -q
# or
npm test
# or
cargo test
```

Confirm: zero failures, zero new skips.

### 2. Lint / Format

```bash
ruff check .          # Python
eslint .              # JS/TS
cargo clippy          # Rust
```

Confirm: zero errors. Warnings are acceptable if documented.

### 3. Type check (if applicable)

```bash
mypy .                # Python
tsc --noEmit          # TypeScript
```

### 4. Security scan

```bash
# Check for known vulnerabilities
pip-audit             # Python
npm audit             # JS/TS
cargo audit           # Rust
```

Confirm: no critical/high vulnerabilities.

### 5. Diff review

```bash
git diff main --stat
```

- Every file changed traces to a ticket/issue.
- No drive-by refactors.
- No commented-out code.
- No debug prints or console.logs.

### 6. Environment check

- `.env` changes documented.
- Database migrations tested.
- Config changes backward-compatible.

### 7. Monitoring

- Key metrics identified (latency, error rate, throughput).
- Alerts configured for regressions.
- Rollback plan documented.

## Verification

- All 7 checks pass.
- Diff is scoped to the stated goal.
- Rollback plan exists and is tested.
