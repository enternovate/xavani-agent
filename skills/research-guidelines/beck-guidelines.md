---
name: beck-guidelines
description: Kent Beck's principles for software craft — test-driven development, simple design, incremental delivery, and the courage to refactor without fear.
domain: software-craft
mandatory: true
priority: 88
version: 1.0
sources:
  - "Test-Driven Development by Example (Addison-Wesley, 2003)"
  - "Tidy First? (O'Reilly, 2023)"
  - "Extreme Programming Explained (Addison-Wesley, 2nd ed.)"
  - "Kent Beck — Tidy Code (kentbeck.substack.com)"
---

# Kent Beck — Operating Guidelines

> "Make the change easy, then make the easy change."

## Core Principles (always-on)

1. **Test first, code second.** Write a failing test that describes the behaviour you want, then write the minimum code to make it pass. The test is the specification; the code is the implementation.

2. **Refactor with a green bar.** Never refactor when the tests are red. Get to green first, then clean up. Refactoring without tests is not refactoring — it is guessing.

3. **Simple design is the goal.** The four criteria: passes all tests, reveals intention, no duplication, fewest elements. If adding code does not improve one of these, do not add it.

4. **Small steps, always.** Commit often. Deploy often. Every change should be small enough that you can undo it without pain. If a change takes more than 15 minutes to explain, it is too large.

5. **Courage to delete.** If code is not serving a purpose, delete it. Dead code is not a safety net — it is a cognitive burden. Version control remembers; you do not need to.

6. **Behaviour is the contract.** Tests verify behaviour, not implementation. If you change the implementation and the tests still pass, the change was safe. If the tests break, you changed the contract.

## Heuristics for the agent

- Before writing any code, **write a test that fails** — then make it pass.
- If a function exceeds 10 lines, **ask whether it can be decomposed** without losing clarity.
- When you find duplication, **extract it only on the third occurrence** — two is a coincidence, three is a pattern.
- If you are afraid to change code, **the tests are insufficient** — add more tests, then change confidently.
- When reviewing code, **check that every branch has a test** — untested branches are bugs waiting to happen.

## Anti-patterns to reject

- "I'll add tests later" — later never comes. Test now.
- "This is too simple to test" — simple code breaks in simple ways; test it.
- "The test is hard to write" — the design is wrong. Simplify the code until the test is easy.
- "I need to refactor this entire module" — no. Refactor one small piece, verify, repeat.

## When to invoke

- Writing any new code, feature, or fix.
- Before refactoring — ensure green tests first.
- When you catch yourself writing code without a test.
