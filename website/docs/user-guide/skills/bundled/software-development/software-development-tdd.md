---
title: "Tdd — Test-driven development — red-green-refactor cycle"
sidebar_label: "Tdd"
description: "Test-driven development — red-green-refactor cycle"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Tdd

Test-driven development — red-green-refactor cycle. Write the test first, make it pass, then clean up.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/tdd` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Test-Driven Development

> "The test is the specification. The code is the implementation."

## When to use

- Writing any new feature or function.
- Fixing a bug (write a test that reproduces it first).
- Refactoring (ensure tests pass before and after).

## Prerequisites

- Test framework installed (pytest, jest, cargo test, etc.).

## Steps

### 1. RED — Write a failing test

Write the smallest test that describes the behaviour you want:

```python
def test_adds_two_numbers():
    assert add(2, 3) == 5
```

Run it. It should fail (the function doesn't exist yet).

### 2. GREEN — Make the test pass

Write the minimum code to make the test pass:

```python
def add(a, b):
    return a + b
```

Run the test. It should pass.

### 3. REFACTOR — Clean up

Now that the test protects you, clean the code:
- Remove duplication.
- Improve naming.
- Simplify logic.

Run the test again. It should still pass.

### 4. Repeat

Write the next test. Each test should:
- Test one behaviour.
- Be independent of other tests.
- Have a clear name that describes what it tests.

## Examples

**Feature: string reversal**
1. Test: `assert reverse("hello") == "olleh"` → FAIL
2. Code: `def reverse(s): return s[::-1]` → PASS
3. Refactor: (already clean)
4. Test: `assert reverse("") == ""` → FAIL
5. Code: handles empty string → PASS
6. Test: `assert reverse("a") == "a"` → FAIL
7. Code: handles single char → PASS

**Bug fix:**
1. Test: reproduce the bug with a specific input → FAIL
2. Code: fix the bug → PASS
3. Refactor: clean up the fix

## Verification

- Every function has at least one test.
- Tests are written before the code.
- All tests pass after every change.


## Provenance

Xavani-original (written from scratch for Xavani, inspired by common TDD patterns).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
