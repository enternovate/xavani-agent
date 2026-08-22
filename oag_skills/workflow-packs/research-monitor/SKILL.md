---
name: research-monitor
description: >
  Research monitor pack: recurring digest over sources with dedupe so repeat runs only surface new material.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [research,digest,monitoring,dedupe]
---

# Research Monitor Pack

## Procedure
1. Keep the digest state file: topic -> seen-item hashes.
2. Collect new items from the user's named sources.
3. Hash titles+URLs; skip anything already in the state file.
4. Summarize only new items, newest first, with source links.
5. Update the state file after delivery.

## Output contract
- Digest header with run date and new-item count.
- Per item: title, link, two-sentence summary.
- "Nothing new" line when zero items pass dedupe.
