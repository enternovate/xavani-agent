---
name: karpathy-guidelines
description: Andrej Karpathy's principles for building AI systems — minimal code, evaluation-driven, read-every-line, bottom-up understanding.
domain: ai-engineering
mandatory: true
priority: 100
version: 1.0
sources:
  - https://karpathy.ai
  - https://github.com/karpathy/nanoGPT
  - https://github.com/karpathy/micrograd
  - https://github.com/karpathy/minbpe
  - "Software 2.0 essay (medium.com/@karpathy)"
  - "Let's build GPT (YouTube)"
  - "A Recipe for Training Neural Networks (karpathy.github.io)"
---

# Andrej Karpathy — Operating Guidelines

> "The best code is no code at all. The next best is code you can read in one sitting."

## Core Principles (always-on)

1. **Eval is all you need.** Before writing one line of "improvement" code, write the test that tells you whether it improved anything. If you cannot measure it, you cannot improve it. Build the eval harness *first*, then the feature.

2. **Read every line.** No magic functions. No "I'll trust the library." If a tensor reshape exists in the code path, you should know its dimensions. The whole point of `nanoGPT` and `micrograd` is that you can hold the entire program in your head.

3. **Minimal code, no abstractions you haven't earned.** Premature abstraction is worse than copy-paste. Start with one concrete file. Extract a base class only after the third instance demands it.

4. **Bottom-up understanding.** Build from the simplest possible mechanism. To understand attention, write it as four matrix multiplies before you reach for `nn.MultiheadAttention`. To understand backprop, write `micrograd` before you reach for `torch.autograd`.

5. **Concrete > Abstract.** One worked example beats five paragraphs of theory. Show the runnable code, the actual tensor shapes, the actual loss curve. Diagrams beat prose. Numbers beat adjectives.

6. **Treat the model like software.** Tests, observability, version control, reproducibility. "It worked on my checkpoint" is not a defense. Pin random seeds. Log every hyperparameter. Diff your config files.

## Operating rules

1. **Think before coding.** State assumptions explicitly. If uncertain, ask. If multiple interpretations exist, present them — don't pick silently. If a simpler approach exists, say so. Push back when warranted.

2. **Simplicity first.** Minimum code that solves the problem. Nothing speculative. No features beyond what was asked. No abstractions for single-use code. No "flexibility" or "configurability" that wasn't requested. If you write 200 lines and it could be 50, rewrite it.

3. **Surgical changes.** Touch only what you must. Clean up only your own mess. Don't "improve" adjacent code, comments, or formatting. Don't refactor things that aren't broken. Remove imports/variables/functions your changes made unused. Every changed line should trace directly to the user's request.

4. **Goal-driven execution.** Transform tasks into verifiable goals. Define success criteria before starting. For multi-step tasks, state a brief plan with per-step verification checkpoints. Strong criteria let you loop independently. Weak criteria require constant clarification.

## Heuristics for the agent

- Before claiming a fix works, **show the measurement** that proves it.
- When asked to implement, **prefer the smallest viable implementation** and call out any added complexity explicitly.
- If a library call exceeds five lines of behaviour, **inline the relevant logic** with a comment so the reader can trace it.
- When unsure between two approaches, **build the smaller one first and benchmark**.
- If you read >200 lines without writing a test, **stop and write a test**.

## Anti-patterns to reject

- "I added a feature flag for future flexibility" — YAGNI, delete it.
- "This abstraction will pay off later" — show the second concrete user first.
- "The framework handles that" — open the framework and confirm.
- "Looks reasonable" without a measurement — restate as a hypothesis with a test.

## When to invoke

- New feature, refactor, or model change → start here.
- Anytime someone proposes adding "flexibility," "configurability," or "extension points."
- Anytime an eval suite is missing for a behaviour you're about to ship.
