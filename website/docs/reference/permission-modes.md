---
sidebar_position: 5
title: "Permission Modes"
description: "Permission Modes — Xavani 0.2.0 reference"
---

# Permission Modes

Xavani gates every non-read tool call behind an approval system with
three modes.

## Modes
- **gated** — every dangerous call asks first. Default for new installs.
- **session-trust** — approvals you grant last for this session only.
- **unrestricted** — no prompts; Xavani prints a one-line warning at start.

## The allowlist
`~/.xavani/permissions.json` stores permanent approvals. Patterns are
exact commands, prefix wildcards, or tool names. Manage them in chat
with `/permissions list|add|remove|clear`.

## Extras
- **Batch preview** — when two or more dangerous commands land in one
  turn, one prompt covers the whole batch.
- **Dry-run** — `/dryrun` makes mutating tools report instead of execute.
- **Undo journal** — every approved write records an inverse patch;
  `/revert [N]` rolls back the last N journaled writes.
- **Audit log** — decisions land in `~/.xavani/permissions.log`.

Run `xavani doctor` to check your permissions file health.
