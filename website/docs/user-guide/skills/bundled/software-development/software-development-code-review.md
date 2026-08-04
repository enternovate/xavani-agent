---
title: "Code Review — Structured code review — check correctness, security, readability, and test coverage before merging"
sidebar_label: "Code Review"
description: "Structured code review — check correctness, security, readability, and test coverage before merging"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Code Review

Structured code review — check correctness, security, readability, and test coverage before merging.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/code-review` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Code Review

> "Every line of code should be read by someone who did not write it before it ships."

## When to use

- Reviewing a pull request.
- Self-reviewing your own code before pushing.
- Pair programming review.

## Prerequisites

- Access to the diff.
- Understanding of the codebase conventions.

## Steps

### 1. Read the description

Understand what the change is trying to do before reading the code.
If there's no description, ask for one.

### 2. Check correctness

- Does the code do what the description says?
- Are edge cases handled?
- Are error paths handled?
- Is the logic correct?

### 3. Check readability

- Can you understand each function in isolation?
- Are names descriptive?
- Are there unnecessary comments? (Code should be self-documenting)
- Are there missing comments where logic is non-obvious?

### 4. Check tests

- Are there tests for the new behavior?
- Do tests cover edge cases?
- Are tests independent?
- Do tests actually assert the right thing?

### 5. Check security

- Is user input validated?
- Are SQL queries parameterised?
- Are secrets handled correctly?
- Is authorization checked?

### 6. Check performance

- Are there N+1 queries?
- Are there unnecessary allocations?
- Is caching used where appropriate?

### 7. Provide feedback

- Be specific: point to exact lines.
- Explain *why*, not just *what*.
- Distinguish blockers from suggestions.
- Praise good code when you see it.

## Verification

- Every concern is actionable and specific.
- Blockers are clearly separated from suggestions.
- The review is complete (no unchecked areas).

## Provenance

Xavani-original (written from scratch for Xavani, based on common code review
practices and industry standards).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
