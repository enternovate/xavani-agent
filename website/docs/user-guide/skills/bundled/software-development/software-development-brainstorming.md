---
title: "Brainstorming — Structured brainstorming — generate, evaluate, and select ideas systematically"
sidebar_label: "Brainstorming"
description: "Structured brainstorming — generate, evaluate, and select ideas systematically"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Brainstorming

Structured brainstorming — generate, evaluate, and select ideas systematically.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/brainstorming` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Brainstorming

> "The best ideas come after the obvious ones are exhausted."

## When to use

- Facing a design decision with multiple valid approaches.
- Exploring solutions to a complex problem.
- Planning a new feature or system.

## Prerequisites

- Clear problem statement.
- Understanding of constraints.

## Steps

### 1. Define the problem

Write one sentence: what are we trying to solve?
Be specific. "Make it faster" is not a problem. "Reduce API latency from 2s to 200ms" is.

### 2. Generate ideas (diverge)

Set a timer (5 minutes). Write every idea, no matter how bad:
- Obvious solutions.
- Wild ideas.
- Things that won't work (and why).
- Combinations of other ideas.

Aim for 10+ ideas. Do NOT evaluate yet.

### 3. Evaluate (converge)

For each idea, score on two axes:
- **Impact:** How much does it solve the problem? (1-5)
- **Feasibility:** How hard is it to implement? (1-5, 5=easy)

Score = Impact × Feasibility. Sort by score.

### 4. Select top 3

Pick the top 3 by score. For each:
- One sentence: what it is.
- One sentence: why it's good.
- One sentence: what could go wrong.

### 5. Decide

If one is clearly best, choose it. If not:
- Can you prototype 2 of them in 1 hour each?
- Can you combine the best parts?
- What does the user care about most?

### 6. Document

Write the decision and rationale. Future you will thank present you.

## Verification

- At least 5 ideas were generated.
- Top 3 were evaluated with concrete criteria.
- A decision was made and documented.


## Provenance

Xavani-original (written from scratch for Xavani, inspired by structured ideation frameworks).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
