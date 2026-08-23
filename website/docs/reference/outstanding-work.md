---
sidebar_position: 18
title: "Outstanding Work"
description: "Cross-session outstanding-work ledger — Xavani 0.3.0 reference"
---

# Outstanding Work

The outstanding ledger remembers unfinished work across sessions. It
powers the desktop reminder banner and gives you one list of open goals,
loops, and tasks from every past conversation.

## Where it lives

`~/.xavani/outstanding.jsonl` — append-only JSONL, file mode 0600.
Each entry carries a number, timestamp, kind (goal, loop, or todo),
text, and status (open, done, cancelled).

## Commands

```
/outstanding              # list all open items
/outstanding done <N>     # close item N as completed
/outstanding cancel <N>   # close item N as cancelled
```

Items stay on the list — and keep reminding you — until you close them.

## Desktop integration

The desktop app shows a reminder notice at launch and every 30 minutes
while open items exist. Click the notice to jump to your task list.
Open goals also appear in the ambient activity pill in the top bar.

## Related

- Persistent todos live in `~/.xavani/todos.json`; manage them in the
  dock To-Do pane. The ledger tracks session-level goals; the To-Do pane
  tracks step-by-step tasks.
