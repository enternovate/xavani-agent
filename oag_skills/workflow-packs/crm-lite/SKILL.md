---
name: crm-lite
description: >
  CRM-lite pack: contact notes and follow-up reminders without any external service.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [contacts,crm,followup,reminders]
---

# CRM-lite Pack

## Procedure
1. Store contacts as markdown cards: name, org, role, last touch, notes.
2. Every interaction appends a dated note line.
3. Follow-ups: contact + date + reason. Overdue follow-ups surface first.
4. Never delete history; supersede notes with new dated entries.

## Output contract
- Contact card on lookup.
- Due-followups table sorted by age.
