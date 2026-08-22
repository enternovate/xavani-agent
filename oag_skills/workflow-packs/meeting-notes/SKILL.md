---
name: meeting-notes
description: >
  Meeting notes pack: turn a transcript or notes file into decisions, owners, deadlines, and follow-up tickets.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [meetings,decisions,owners,tickets]
---

# Meeting Notes Pack

## Procedure
1. Read the transcript or raw notes.
2. Extract DECISIONS as one line each with the deciding person.
3. Extract ACTION ITEMS as owner + task + deadline.
4. Flag open questions nobody answered.
5. Render the summary table and ask which tickets to create.

## Output contract
- Decisions table: decision, owner, rationale.
- Actions table: owner, action, due date.
- Open questions list.
