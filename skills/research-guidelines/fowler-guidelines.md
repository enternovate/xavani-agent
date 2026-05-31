---
name: fowler-guidelines
description: Martin Fowler's principles for software craftsmanship — refactoring as discipline, continuous integration, architectural clarity, and the courage to improve code incrementally.
domain: software-craft
mandatory: true
priority: 86
version: 1.0
sources:
  - "Refactoring: Improving the Design of Existing Code (2nd ed., Martin Fowler)"
  - "martinfowler.com (code smells, CI/CD, architectural patterns)"
  - "Patterns of Enterprise Application Architecture"
  - "Continuous Integration (martinfowler.com)"
---

# Martin Fowler — Operating Guidelines

> "Any fool can write code that a computer can understand. Good programmers write code that humans can understand."

## Core Principles (always-on)

1. **Refactor continuously, not in big bangs.** Small, frequent refactorings keep the codebase healthy. Large refactoring efforts are risky, expensive, and often abandoned halfway. Refactor a little, test, commit, repeat.

2. **Code smells are signals, not crimes.** A code smell (duplication, long method, feature envy) is a hint that something might be wrong. Investigate before refactoring — not every smell needs fixing, but every smell deserves attention.

3. **Continuous integration is a discipline, not a tool.** Merge to main at least daily. Run all tests on every merge. If integration hurts, do it more often — that is how you find and fix the pain.

4. **Architecture is about boundaries.** Good architecture separates what changes from what stays stable. The domain model should not know about the database. The UI should not know about the business rules. Boundaries make change safe.

5. **Premature optimisation is the root of all evil — but premature pessimation is worse.** Do not optimise without a measurement. But do not write obviously slow code either. Get it right, get it clean, then make it fast — measured.

6. **Tests are a design tool, not a verification tool.** Writing tests first forces you to think about the interface before the implementation. If the test is hard to write, the design is wrong.

## Heuristics for the agent

- Before refactoring, **ensure you have tests that cover the current behaviour** — refactor without tests is guessing.
- If you see the same code in three places, **extract it** — but only if the abstraction is obvious.
- When a function exceeds 20 lines, **look for an opportunity to extract** — but do not extract just for the sake of it.
- If a change requires touching files in 5 different directories, **the architecture may need rethinking**.
- When reviewing code, **look for code smells**: long methods, deep nesting, feature envy, data clumps.

## Anti-patterns to reject

- "We'll refactor later" — later means never. Refactor now, in small steps.
- "The tests are too slow to run" — slow tests are a symptom of a design problem. Fix the design.
- "It's too risky to change" — if it is too risky to change, the tests are insufficient.
- "We need a big rewrite" — no. You need many small improvements. Big rewrites almost always fail.

## When to invoke

- Before making any change to existing code.
- When you notice code smells: duplication, long methods, deep nesting.
- When integration is painful or tests are slow.
