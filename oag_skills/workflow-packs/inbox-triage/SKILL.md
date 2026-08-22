---
name: inbox-triage
description: >
  Inbox triage pack: prioritize mail into urgent/respond/delegate/read buckets, draft replies for the top bucket, and verify sends before delivery.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [email,triage,inbox,priority]
---

# Inbox Triage Pack

## Procedure
1. List unread mail with subject, sender, and age.
2. Sort into four buckets: URGENT (today), RESPOND (this week),
   DELEGATE, READ-LATER.
3. For each URGENT and RESPOND thread, draft one reply.
4. Show every draft for approval. Send nothing without confirmation.
5. After sending, verify delivery. Report per-bucket counts.

## Output contract
- One table: bucket, count, oldest item age.
- One draft block per reply with To/Subject/Body.
- A final send log: sent, failed, skipped.
