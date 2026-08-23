---
sidebar_position: 20
title: "Preview Control"
description: "Agent-driven desktop preview dock — Xavani 0.3.0 reference"
---

# Preview Control

Inside the Xavani desktop app, the agent can drive the preview dock on
your behalf: open a dev server, navigate, close, or check status.

## The tool

```
preview_control(action="open", url="http://localhost:3000")
preview_control(action="navigate", url="http://localhost:3001/pricing")
preview_control(action="close")
preview_control(action="status")
```

## Availability

The tool activates only when the engine runs inside the desktop app
(detected through `XAVANI_DESKTOP_API`). In a terminal session it
returns a clear message instead of failing. CLI sessions are unaffected.

## How it works with visual editing

You and the agent share the same dock:

- You click **Visual edit**, adjust elements by hand, and apply. Each
  change maps to real workspace files and reaches the agent as a precise
  edit brief with file names and line numbers.
- The agent can open or navigate the preview itself while working — for
  example to verify a page after a code change.

Every applied change passes the standard write-approval flow, so nothing
modifies your files without review.
