---
title: "Verification Before Completion"
sidebar_label: "Verification Before Completion"
description: "Verify work is actually done before declaring completion — run tests, check edge cases, show evidence"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Verification Before Completion

Verify work is actually done before declaring completion — run tests, check edge cases, show evidence.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/verification-before-completion` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Verification Before Completion

> "Done means tested, not typed."

## When to use

- Before saying "this is done."
- Before merging a PR.
- Before closing an issue.

## Prerequisites

- The code change is written.
- You believe it works.

## Steps

### 1. Run the tests

```bash
pytest -q           # Python
npm test            # JS/TS
cargo test          # Rust
```

Show the output. If you can't show it, it didn't happen.

### 2. Check edge cases

For every change, verify:
- Empty input.
- Maximum input.
- Null/None/undefined.
- Special characters.
- Concurrent access (if applicable).

### 3. Show the evidence

Don't say "it works." Show:
- Test output (pass rate, coverage).
- A screenshot or terminal output.
- A before/after comparison.

### 4. Verify the original requirement

Re-read the original request. Does your change actually address it?
- If the request was "fix the bug," does the bug no longer reproduce?
- If the request was "add the feature," does the feature work as described?

### 5. Check for regressions

Did your change break anything else?
- Run the full test suite (not just your new tests).
- Check related features.
- Look for unintended side effects.

### 6. Document what you did

One paragraph: what changed, why, and how to verify it.

## Verification

- Tests pass and output is shown.
- Edge cases are verified.
- Original requirement is met.
- No regressions introduced.


## Provenance

Xavani-original (written from scratch for Xavani, inspired by quality gate patterns).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
