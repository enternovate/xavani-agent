---
name: polya-guidelines
description: George Pólya's "How to Solve It" — understand, plan, execute, review; the discipline of heuristics for hard problems.
domain: problem-solving
mandatory: true
priority: 95
version: 1.0
sources:
  - "How to Solve It (Pólya 1945)"
  - "Mathematics and Plausible Reasoning (Pólya 1954)"
  - "Mathematical Discovery (Pólya 1962/1965)"
---

# George Pólya — Operating Guidelines

> "If you can't solve a problem, then there is an easier problem you can't solve: find it."

## Core Principles (always-on)

1. **Understand the problem first.** Restate it in your own words. Identify the unknown, the data, and the condition that links them. Most failed attempts skip this step.

2. **Devise a plan.** Search for analogies. Have you seen a related problem? Can you solve a sub-problem? Can you solve an easier related problem? The plan is the bridge between understanding and execution.

3. **Carry out the plan.** Check each step. Verify each step is correct, not just that the conclusion looks plausible.

4. **Look back.** After you finish, review: is the result correct? Could you have derived it more directly? Does the method generalise? Reviewing is how heuristics compound.

5. **Use heuristics, not just deductive rules.** Try the simpler case. Vary the problem. Draw a figure. Consider the converse. Specialise to a concrete instance. Generalise to a wider class.

6. **When stuck, weaken or strengthen the goal.** If you cannot solve the original, find a related problem you can solve and use the insight to attack the original.

## Heuristics for the agent

- Before writing code, **restate the problem in your own words** and confirm the unknown / data / condition.
- When stuck, **try the simplest non-trivial instance** of the problem.
- When stuck, **list the assumptions** — at least one is often wrong.
- After solving, ask: **does this generalise?** And: **could I have done it more directly?**
- Maintain a **catalogue of heuristics** — analogy, special case, varying conditions, working backward — and consult it explicitly.

## Anti-patterns to reject

- "I'll start coding and see what happens" — half the bugs come from a vague understanding of the goal.
- "It works on the example, ship it" — without "looking back" you lose the chance to generalise.
- "There's no analogy here" — there almost always is; look harder.

## When to invoke

- Any novel problem with no obvious template.
- Debugging when the cause is unclear.
- Designing algorithms or proofs.
