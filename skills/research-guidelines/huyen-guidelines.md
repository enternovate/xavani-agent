---
name: huyen-guidelines
description: Chip Huyen's principles for production ML systems — data-centric thinking, monitoring-first, iterative deployment, and the discipline of making models survive contact with real users.
domain: ml-systems
mandatory: true
priority: 90
version: 1.0
sources:
  - "Designing Machine Learning Systems (O'Reilly, 2022)"
  - "AI Engineering (O'Reilly, 2025)"
  - "Chip Huyen — Machine Learning Systems Design (huyenchip.com)"
  - "Real-time Machine Learning (huyenchip.com)"
---

# Chip Huyen — Operating Guidelines

> "A model is only as good as the data it's trained on, the system it's deployed in, and the monitoring that keeps it honest."

## Core Principles (always-on)

1. **Data quality trumps model complexity.** Before tuning hyperparameters, clean the data. Before adding layers, fix the labels. A simple model on clean data beats a complex model on noisy data — every time.

2. **Monitoring is not optional.** A deployed model without monitoring is a time bomb. Track input distribution, prediction distribution, latency, error rate, and business metrics from day one. If you cannot detect drift, you cannot prevent failures.

3. **Iterate in production, not in notebooks.** The notebook is where you explore; production is where you learn. Get a minimal model deployed fast, then iterate with real feedback. Perfect is the enemy of deployed.

4. **Feature engineering is where the intelligence lives.** The model is a function approximator; the features are where domain knowledge enters. Invest in understanding the data pipeline, not in finding the latest architecture.

5. **Think in systems, not models.** A model is one component in a pipeline that includes data collection, feature computation, serving, monitoring, and feedback loops. Optimising the model while ignoring the system is local optimisation.

6. **Reproducibility is a requirement, not a luxury.** Pin data versions, model versions, feature versions, and environment versions. If you cannot reproduce a result, you do not understand it.

## Heuristics for the agent

- Before adding a model, **check if a heuristic or rule-based system solves the problem** — it is cheaper, faster, and more debuggable.
- When a model degrades in production, **check the input data first** before blaming the model.
- If a feature takes more than a paragraph to explain, **it is probably too complex** — simplify or decompose it.
- When deploying, **start with shadow mode** — run the new model alongside the old one and compare before switching.
- If monitoring shows a metric drifting, **treat it as a bug**, not as "expected variance."

## Anti-patterns to reject

- "We'll add monitoring after launch" — you will not; you will be fighting fires instead.
- "The training data represents production" — it does not; production distributions shift.
- "We need the latest model" — check if the current model, with better data, outperforms the new one.
- "The notebook metric is good enough" — notebook metrics and production metrics live in different universes.

## When to invoke

- Designing an ML pipeline or system architecture.
- Evaluating whether to deploy a new model or improve the existing one.
- When production metrics start drifting or degrading.
