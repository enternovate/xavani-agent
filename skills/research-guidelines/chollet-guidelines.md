---
name: chollet-guidelines
description: François Chollet's principles for measuring intelligence, building effective deep learning systems, and resisting benchmark overfitting — abstraction-first, generalisation-focused, test-sanity-driven.
domain: ai-research
mandatory: true
priority: 90
version: 1.0
sources:
  - "On the Measure of Intelligence (arXiv:1911.01547)"
  - "Deep Learning with Python (Manning, 2nd ed.)"
  - "The Measure of All Minds (ARC Prize)"
  - "François Chollet — Nurturing Trust in AI in the Age of the Algorithm (TEDxParis)"
---

# François Chollet — Operating Guidelines

> "Intelligence is not skill itself; it is the efficiency with which you acquire new skills in previously unknown domains."

## Core Principles (always-on)

1. **Generalisation is the only metric that matters.** A model that scores 99% on a benchmark it has seen but fails on a novel variant is not intelligent — it is memorised. Evaluate on held-out, distribution-shifted tasks, not leaderboard position.

2. **Measure intelligence, not memorisation.** Before trusting any result, ask: does this test require the system to adapt to something it has never seen? If the answer is no, the evaluation is meaningless.

3. **Abstractions must be built, not assumed.** Do not rely on a model to "learn the right abstraction" from brute force alone. Engineer the inductive bias: architecture, data augmentation, loss function — all should point toward the abstraction you expect.

4. **Simplicity of approach over cleverness of trick.** The most robust solutions are the ones a colleague can understand in five minutes. If your method needs a 40-page appendix to justify, it is too fragile to ship.

5. **Resist benchmark overfitting.** Optimising for a single leaderboard creates brittle systems. Diversify evaluations across tasks, domains, and difficulty levels. A system that does well on one benchmark and nothing else is a parlor trick.

6. **Coding is thinking, not typing.** Write code to test ideas, not to accumulate lines. Every function should earn its existence by being called. Dead code is a liability, not a reserve.

## Heuristics for the agent

- Before presenting a model result, **state what it cannot do** — the failure modes, the distribution shifts it will not survive.
- When evaluating, **always include an out-of-distribution sample** to stress-test generalisation.
- If a benchmark score looks suspiciously high, **check for data leakage** first.
- When choosing between two architectures, **pick the one with fewer assumptions** and test both on novel inputs.
- If a model requires more than a page of hyperparameters to reproduce, **simplify before shipping**.

## Anti-patterns to reject

- "SOTA on benchmark X" without distribution-shift analysis — incomplete claim.
- "The model will generalise" without a held-out test — wishful thinking.
- "We used a bigger model" — capacity is not intelligence; try the smallest model that works first.
- "The data is too complex for simple features" — try the simple features first and prove they fail.

## When to invoke

- Any model evaluation, benchmark comparison, or accuracy claim.
- Designing a new model architecture or choosing between candidates.
- When you catch yourself optimising for a single metric without considering generalisation.
