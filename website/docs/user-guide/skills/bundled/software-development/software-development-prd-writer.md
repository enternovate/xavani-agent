---
title: "Prd Writer — Write Product Requirements Documents that engineers can actually implement"
sidebar_label: "Prd Writer"
description: "Write Product Requirements Documents that engineers can actually implement"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Prd Writer

Write Product Requirements Documents that engineers can actually implement.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/prd-writer` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# PRD Writer

> "A PRD that an engineer cannot implement in a week is not a PRD — it is a wish."

## When to use

- Defining a new feature before engineering starts.
- Scoping a product initiative.
- Aligning stakeholders on what gets built.

## Prerequisites

- Clear user problem identified.
- Success metrics defined.
- Stakeholder alignment on scope.

## Steps

### 1. Problem and user story

"As a [user type], I want [capability] so that [benefit]."

### 2. Success metrics

Define 2-3 measurable outcomes:
- Metric name
- Current baseline
- Target value
- Measurement method

### 3. User experience

Describe the flow:
1. User does X.
2. System responds with Y.
3. User sees Z.

Include wireframes or mockups if available.

### 4. Functional requirements

List requirements as user-facing behaviors, not implementation details:
- "User can filter results by date range" (not "add a date picker component")
- Each requirement should be testable.

### 5. Non-functional requirements

- Performance: page loads in &lt;2s.
- Availability: 99.9% uptime.
- Security: data encrypted at rest and in transit.
- Accessibility: WCAG 2.1 AA.

### 6. Out of scope

Explicitly list what will NOT be built. This prevents scope creep.

### 7. Timeline and milestones

| Milestone | Target Date | Owner |
|-----------|------------|-------|
| Design complete | ... | ... |
| MVP shipped | ... | ... |
| Full launch | ... | ... |

## Verification

- Every requirement is testable.
- Success metrics have baselines and targets.
- Out of scope is explicitly listed.
- Timeline has concrete dates and owners.
