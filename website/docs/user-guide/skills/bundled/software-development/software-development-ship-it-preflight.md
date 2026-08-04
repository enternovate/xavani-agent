---
title: "Ship It Preflight — Pre-release checklist — verify all gates pass before shipping code to production"
sidebar_label: "Ship It Preflight"
description: "Pre-release checklist — verify all gates pass before shipping code to production"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Ship It Preflight

Pre-release checklist — verify all gates pass before shipping code to production.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/ship-it-preflight` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

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
