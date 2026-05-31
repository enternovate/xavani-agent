---
name: yan-guidelines
description: Eugene Yan's patterns for building LLM-based systems and products — pragmatic engineering, user-centric design, evaluation-driven iteration, and the discipline of shipping real systems.
domain: ai-engineering
mandatory: true
priority: 90
version: 1.0
sources:
  - "Patterns for Building LLM-based Systems & Products (eugeneyan.com, 2023)"
  - "Evaluating LLM Systems (eugeneyan.com)"
  - "RecSys in the Age of LLMs (eugeneyan.com)"
  - "Eugene Yan — Applied ML (eugeneyan.com)"
---

# Eugene Yan — Operating Guidelines

> "The best systems are not the ones with the most sophisticated models — they are the ones where every component is observable, debuggable, and replaceable."

## Core Principles (always-on)

1. **Start with the product, not the model.** What does the user need? What is the failure mode they will notice? Build backward from the user experience, not forward from the model's capabilities.

2. **Evaluate with production traffic, not curated sets.** The eval set must reflect real user behaviour — messy, diverse, adversarial. If your eval set is too clean, your model will be too fragile.

3. **Observability beats accuracy.** A model you can debug is worth more than a model that is 2% more accurate but opaque. Instrument everything: inputs, outputs, intermediate states, latency, cost.

4. **Ship iteratively, measure relentlessly.** Every deployment is an experiment. A/B test, measure, learn, iterate. Do not ship and forget — ship and watch.

5. **Simple pipelines outperform complex ones.** A retrieval-augmented prompt with a verification step will outperform a multi-agent orchestration that nobody can debug. Complexity is a cost; pay it only when the ROI is clear.

6. **User feedback is the ground truth.** Automated metrics correlate with user satisfaction, but they are not the same thing. When automated metrics and user feedback disagree, trust the user.

## Heuristics for the agent

- Before building a complex pipeline, **ship the simplest version and measure** — add complexity only when you have evidence it helps.
- When an LLM output is wrong, **check the prompt/context before blaming the model** — most failures are input failures.
- If you cannot explain a system's behaviour in one paragraph, **simplify it**.
- When evaluating, **always include a "hard" set** — cases designed to break the system.
- If user feedback contradicts your metrics, **update your metrics**, not your opinion of the user.

## Anti-patterns to reject

- "We'll evaluate later" — evaluate first, then build. If you cannot measure it, you cannot ship it.
- "The model is a black box" — instrument it. If you cannot see inside, you cannot fix it.
- "More agents = better" — multi-agent systems multiply failure modes; justify each agent's existence.
- "The benchmark is representative" — benchmarks are starting points, not endpoints.

## When to invoke

- Designing an LLM product or feature.
- Choosing between a simple and a complex solution.
- When user feedback contradicts automated metrics.
