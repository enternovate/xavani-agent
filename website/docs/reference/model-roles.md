---
sidebar_position: 8
title: "Model Roles"
description: "Model Roles — Xavani 0.2.0 reference"
---

# Model Roles

Roles let different jobs use different models. Built-in roles:
`default`, `smol`, `slow`, `plan`, `advisor`.

## Configuration
```yaml
model:
  roles:
    advisor: "openrouter/anthropic/claude-sonnet-4"
    smol: "openrouter/meta-llama/llama-3.1-8b-instruct"
```
An explicit `provider/model` override wins over automatic routing.
Without an override, each role resolves through its task class
(for example, advisor maps to the judgment task class).

## Where roles apply
- **advisor** — the `/advisor` reviewer reads each reply on its own
  context and appends severity-tagged notes inline.
- **smol** — cheap fan-out work.
- **plan** — plan-mode reasoning.
- **slow** — long-horizon tasks.

## Judge model for the bench
Set `XAVANI_BENCH_JUDGE_MODEL=<model>` to add a model yes/no verdict
on top of deterministic `llm_judge:` rubric lines.
