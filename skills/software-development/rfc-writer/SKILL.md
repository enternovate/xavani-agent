---
name: rfc-writer
description: Write clear, actionable RFCs (Request for Comments) for technical design decisions.
categories:
  - software-development
platforms:
  - all
tags:
  - design
  - documentation
  - architecture
condition: When proposing a significant technical change, new system, or architectural decision.
---

# RFC Writer

> "A good RFC is a decision that has already been made by the time people read it."

## When to use

- Proposing a new system or service.
- Changing an API or data model.
- Introducing a new dependency or tool.
- Making an architectural decision with trade-offs.

## Prerequisites

- Clear problem statement.
- At least one proposed solution.
- Understanding of constraints (time, team, infra).

## Steps

### 1. Problem statement

Write 2-3 sentences: what is broken, why it matters, what happens if we do nothing.

### 2. Goals and non-goals

**Goals:** what this RFC achieves. Be specific and measurable.
**Non-goals:** what this RFC explicitly does NOT address. This prevents scope creep.

### 3. Proposed solution

Describe the solution in enough detail that someone could implement it:
- Architecture diagram (ASCII or link).
- Data model changes.
- API changes.
- Key algorithms or logic.

### 4. Alternatives considered

List 2-3 alternatives with one paragraph each explaining why they were rejected.

### 5. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ... | High/Med/Low | High/Med/Low | ... |

### 6. Implementation plan

Break into phases:
1. Phase 1: MVP (what ships first)
2. Phase 2: Iteration (what follows)
3. Phase 3: Polish (nice-to-haves)

### 7. Open questions

List anything that needs input before proceeding.

## Verification

- Problem statement is concrete and measurable.
- At least 2 alternatives were considered.
- Risks have mitigations.
- Implementation plan has phases with clear deliverables.
