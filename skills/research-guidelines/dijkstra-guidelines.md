---
name: dijkstra-guidelines
description: Edsger Dijkstra's principles for rigorous programming — mathematical correctness, structured programming, separation of concerns, and the discipline of reasoning about programs before running them.
domain: software-craft
mandatory: true
priority: 84
version: 1.0
sources:
  - "Go To Statement Considered Harmful (Communications of the ACM, 1968)"
  - "A Discipline of Programming (Prentice Hall, 1976)"
  - "EWD manuscripts (cs.utexas.edu/users/EWD/)"
  - "The Humble Programmer (Turing Award Lecture, 1972)"
---

# Edsger Dijkstra — Operating Guidelines

> "Simplicity is a great virtue but it requires hard work to achieve it and education to appreciate it."

## Core Principles (always-on)

1. **Reason about programs before running them.** Testing shows the presence of bugs, not their absence. Think through the logic, the invariants, the edge cases before you execute. A program you cannot reason about is a program you do not understand.

2. **Structured control flow only.** Goto is harmful because it destroys the local reasoning that makes code understandable. Use loops, conditionals, and functions — structures that preserve the relationship between text and execution order.

3. **Separation of concerns is non-negotiable.** Every module, every function, every class should address exactly one concern. When concerns are mixed, you cannot reason about, test, or change one without touching the other.

4. **Invariants are your friends.** A loop invariant tells you what is true before, during, and after the loop. An object invariant tells you what is true about its state. Invariants are the scaffolding of correct programs.

5. **Do not hand-wave complexity.** If you cannot explain the time complexity of your algorithm, you do not understand it. If you cannot bound the memory usage, you have not designed it.

6. **Elegance is not optional.** An elegant program is one in which every part is necessary and no part is sufficient. Elegance is a proxy for correctness — if a solution feels clumsy, it probably has a hidden bug.

## Heuristics for the agent

- Before writing a loop, **state the invariant** — what is true at the start of each iteration?
- If a function has more than one exit point, **ask whether that makes it easier or harder to reason about**.
- When you catch yourself using a flag variable, **ask whether the control flow can be restructured** to eliminate it.
- If a recursive function does not have a clear base case, **stop and define it** before writing the recursive step.
- When reviewing code, **check that every variable has a single, clear purpose** — multi-purpose variables are bugs waiting to happen.

## Anti-patterns to reject

- "I'll just add a flag to handle that case" — flags are code smells. Restructure the logic.
- "It works on my machine" — testing is not proof. Reason about the edge cases.
- "The algorithm is good enough" — good enough for what? State the requirements and measure.
- "We can optimise later" — if you do not understand the complexity now, you will not understand it later.

## When to invoke

- Writing any algorithmic code or data structure manipulation.
- When code has complex control flow — nested loops, multiple exits, flag variables.
- When you are about to say "it should work" without a proof or invariant.
