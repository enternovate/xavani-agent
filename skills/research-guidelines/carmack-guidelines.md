---
name: carmack-guidelines
description: John Carmack's principles for software engineering — performance-aware design, functional purity where possible, ruthless debugging, and the discipline of understanding every byte.
domain: software-craft
mandatory: true
priority: 85
version: 1.0
sources:
  - "Functional Programming in C++ (2018)"
  - ".plan archives (armadillo.planetquake.gamespy.com)"
  - "John Carmack on Inlined Code (2005)"
  - "John Carmack — Quality Assurance (2014)"
---

# John Carmack — Operating Guidelines

> "If you don't understand the performance characteristics of what you're doing, you're programming by coincidence."

## Core Principles (always-on)

1. **Understand the cost of every abstraction.** Every layer of abstraction has a cost — in indirection, in cache misses, in cognitive load. Use abstractions, but know what they cost. If you cannot explain the cost, you do not understand the abstraction.

2. **Functional purity where possible, mutation where necessary.** Pure functions are testable, composable, and parallelisable. Use mutation only when the performance benefit is measured and significant. Default to immutability.

3. **Debug with data, not with intuition.** When something breaks, reproduce it, measure it, isolate it. "I think the problem is..." is not debugging — it is guessing. Use logs, assertions, and binary search to find the root cause.

4. **Inline when clarity demands it.** If a function is called once and is short enough to understand inline, do not extract it. Indirection is a cost; pay it only when it buys you something.

5. **Performance is a feature, not an afterthought.** If you do not measure performance, you will not notice it degrading. Profile before optimising. Optimise the hot path, not the cold one.

6. **Code reviews are the best debugging tool.** The cheapest bug is the one caught in review. Every line of code should be read by someone who did not write it before it ships.

## Heuristics for the agent

- Before adding an abstraction layer, **ask: what does this buy me?** If the answer is "future flexibility," delete it.
- When debugging, **start with the smallest reproducible case** — strip away everything that does not contribute to the bug.
- If a function is called more than 1000 times per second, **profile it** — otherwise, do not optimise.
- When you find a bug, **fix the root cause, not the symptom** — masking symptoms creates harder bugs later.
- If code is hard to test, **it is probably hard to use** — simplify the interface.

## Anti-patterns to reject

- "It's fast enough" — measured with what? Show the benchmark.
- "The abstraction is free" — no abstraction is free. Every one has a cost.
- "It only fails sometimes" — intermittent failures are the most dangerous kind. Find the root cause.
- "The compiler will optimise it" — maybe. Measure first.

## When to invoke

- Writing performance-sensitive code or profiling bottlenecks.
- Debugging an intermittent or hard-to-reproduce issue.
- When you catch yourself adding an abstraction without a concrete reason.
