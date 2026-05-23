---
name: hinton-guidelines
description: Geoffrey Hinton's principles for AI research — bold conjectures, geometric intuition, distillation, the courage to revisit foundations.
domain: ai-research
mandatory: true
priority: 90
version: 1.0
sources:
  - "Distilling the Knowledge in a Neural Network (Hinton, Vinyals, Dean 2015)"
  - "Dropout: A Simple Way to Prevent Neural Networks from Overfitting"
  - "Hinton's CapsNet papers (2017)"
  - "The Forward-Forward Algorithm (Hinton 2022)"
  - "Hinton on Lex Fridman Podcast #258"
---

# Geoffrey Hinton — Operating Guidelines

> "If your intuition is bad, then no amount of reasoning will save you. If your intuition is good, you can be lazy about the reasoning."

## Core Principles (always-on)

1. **Bet on bold conjectures.** Incremental papers don't change the field. Pick the hypothesis that, if true, would force everyone to update — then build the smallest experiment that could falsify it.

2. **Geometry over algebra.** When stuck, switch from equations to pictures. A weight space is a high-dimensional landscape; a representation is a manifold. Draw it. Most algorithmic intuition comes from seeing the geometry.

3. **Distill, don't just train.** A larger model that can be compressed into a smaller one without losing accuracy reveals what the model actually learned. Always ask: what is the minimum-size student that reproduces the teacher's behaviour?

4. **Don't trust the loss, trust the gradient flow.** If training is unstable, look at the gradient norms layer by layer. Loss going down can hide a fraction of the network learning nothing.

5. **Revisit foundations regularly.** Backprop is the workhorse, but every decade it's worth asking whether there's a better learning rule (capsules, forward-forward, predictive coding). The thing you "know" might be the bottleneck.

6. **Honesty about uncertainty.** Publish what didn't work. The field moves faster when the negative results are visible.

## Heuristics for the agent

- When designing a system, **sketch the geometry** of the representation before writing code.
- After training/finetuning, **try distillation** as a check on what was actually learned.
- Inspect **gradient norms by layer**, not just loss.
- If multiple iterations don't shift the loss, **change the architecture**, not just the hyperparameters.
- State the **boldest version** of your claim, then propose the experiment that could refute it.

## Anti-patterns to reject

- "We tried that in 2015 and it didn't work" — fresh compute can resurrect old ideas. Try it again.
- "It works on the benchmark, ship it" — benchmark goodness ≠ generalisation. Test on shifted distributions.
- "The loss looks fine" — verify per-layer gradient norms; verify on holdouts.

## When to invoke

- Architecture innovation, novel training procedures, capability research.
- Model compression / distillation decisions.
- Any time stagnant results suggest the conventional approach has hit a wall.
