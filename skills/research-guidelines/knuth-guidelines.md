---
name: knuth-guidelines
description: Donald Knuth's principles — literate programming, rigorous algorithmic analysis, precision over speed, the discipline of writing programs for humans.
domain: software-craft
mandatory: true
priority: 95
version: 1.0
sources:
  - "The Art of Computer Programming (Knuth, 1968-ongoing)"
  - "Literate Programming (Knuth 1984, The Computer Journal)"
  - "Structured Programming with go to Statements (Knuth 1974)"
  - https://www-cs-faculty.stanford.edu/~knuth/
---

# Donald Knuth — Operating Guidelines

> "Premature optimisation is the root of all evil (or at least most of it) in programming."

## Core Principles (always-on)

1. **Programs are literature.** Write code primarily to be read by humans; secondarily to be executed by machines. Comments explain *why*. Variable names tell the story. Layout follows narrative, not language syntax.

2. **Optimise after measurement, never before.** Profile first, optimise second. The 97% of code that doesn't matter wastes effort if optimised. Identify the 3% hot path and improve only that.

3. **Rigour over hand-waving.** When you claim something runs in O(n log n), prove it. When you claim correctness, write the invariant. The discipline of formal reasoning catches bugs that testing misses.

4. **Master both the algorithm and the constant.** Big-O is necessary but not sufficient. The constant factor decides whether a feature ships. Know both.

5. **Re-derive, don't memorise.** Periodically rebuild the foundations — sorting, hashing, recursion — from first principles. Memorised knowledge atrophies; derived knowledge endures.

6. **Write for the long term.** Today's quick hack is next year's debugging session. The cost of a clear program is paid once; the cost of an opaque one is paid forever.

## Heuristics for the agent

- Before optimising, **measure** — even a one-shot timing comparison beats a guess.
- For any non-trivial function, write **a one-line invariant** in the docstring.
- When choosing between a clever and a clear solution, **default to clear**; clever requires a benchmark to justify it.
- For complexity claims, state the **best, worst, and average case** explicitly.
- Prefer **descriptive names** even at the cost of length.

## Anti-patterns to reject

- "It's O(n) so it's fine" — until you see the constant, it's a guess.
- "I'll comment it later" — later never comes; comments age with the code.
- "It's a one-off script" — most one-offs become two-offs, three-offs, …

## When to invoke

- Performance work, algorithmic decisions.
- Code review and refactoring.
- Documentation and architectural write-ups.
