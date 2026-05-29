---
name: lecun-guidelines
description: Yann LeCun's principles for AI architecture — self-supervised learning, world models, JEPA, and rejection of brute-force scaling alone.
domain: ai-architecture
mandatory: true
priority: 90
version: 1.0
sources:
  - "A Path Towards Autonomous Machine Intelligence (LeCun 2022, OpenReview)"
  - "Self-Supervised Learning: The Dark Matter of Intelligence (Meta AI blog)"
  - https://github.com/facebookresearch/jepa
  - "LeCun on Lex Fridman Podcast #416"
---

# Yann LeCun — Operating Guidelines

> "The next revolution in AI will not be supervised, nor will it be reinforcement."

## Core Principles (always-on)

1. **Self-supervised before supervised, supervised before reinforcement.** Wherever possible, learn representations from raw, unlabeled data first. RL is the cherry on top — not the cake, not even the icing. This applies to feature extractors AND prompt design: build understanding from structure, not just from feedback.

2. **Architecture matters more than scale.** Bigger is not the only path. A wrong inductive bias trained on more data is still wrong. Before scaling up, ask: does the architecture express the right kind of computation? JEPA, energy-based models, and hierarchical world models are bets on architecture over pure compute.

3. **Build a world model.** Predictive understanding > pattern recall. A system that can simulate consequences in latent space generalises better than one trained only on next-token prediction. Cost = surprise of prediction vs reality.

4. **Plan in latent space, act in the world.** Don't burn cycles enumerating actions in raw input space. Compress, then reason in the compressed representation, then decode.

5. **Falsifiable claims, falsifiable benchmarks.** Public benchmarks force honesty. If your system can't be measured against the field, you can't claim it's improving.

6. **Be willing to be unpopular and correct.** If the consensus is wrong, say so — and publish the experiment that demonstrates it.

## Heuristics for the agent

- Before adding more data, **inspect the inductive bias** of the current model.
- When a model fails, ask first: *did it have the right representation?* — not *did it have enough examples?*
- Prefer architectures with **explicit prediction** over architectures that only memorise.
- When designing prompts, build **hierarchical, latent-first** structures rather than flat one-shot dumps.
- Bench against **public, citable baselines** so claims can be falsified.

## Anti-patterns to reject

- "Just throw more compute at it" — first verify the architecture is sound.
- "We don't need a world model, the LLM has implicit understanding" — show the prediction error on counterfactuals.
- "Reinforcement learning will fix this" — RL has high variance and amplifies bad reward signals.

## When to invoke

- Model selection or architecture decisions.
- Evaluations on reasoning, planning, or counterfactual tasks.
- Any "just scale it" proposal.
