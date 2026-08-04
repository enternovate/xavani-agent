---
title: "File Organizer"
sidebar_label: "File Organizer"
description: "Automatically sort Downloads/Desktop/Documents into category folders — safe, reversible, with a real-time watcher"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# File Organizer

Automatically sort Downloads/Desktop/Documents into category folders — safe, reversible, with a real-time watcher.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/productivity/file-organizer` |
| Version | `1.0.0` |
| Author | Enternovate |
| License | MIT |
| Platforms | linux, macos, windows |
| Tags | `Files`, `Automation`, `Productivity`, `Cleanup`, `Watcher` |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# file-organizer

Keep the user's everyday folders tidy by sorting loose files into category
subfolders — `Images/`, `PDFs/`, `Documents/`, `Spreadsheets/`,
`Presentations/`, `Archives/`, `Audio/`, `Video/`, `Code/`, `Data/`,
`Installers/`, `Screenshots/`, `Other/`.

It can run **once on demand** or **continuously in the background** ("real-time"),
watching for new files and filing them as they land.

## Safety guarantees

This moves real files, so it is conservative by design:

- **Never deletes** anything — only moves.
- **Never overwrites** — a name clash becomes `report (1).pdf`, not a lost file.
- **Skips files mid-write** — partial downloads (`.crdownload`, `.part`, …) and
  anything modified in the last ~10s are left alone.
- **Skips hidden/system files** (`.DS_Store`, `Thumbs.db`, dotfiles).
- **Idempotent** — running again does nothing; it never re-files an
  already-sorted file.
- **Fully reversible** — every move is logged to a manifest so `undo` puts
  everything back.

## Using it through the agent (`organize_files` tool)

Always **preview first** so the user sees the plan, then organize:

| mode          | what it does                                              |
|---------------|----------------------------------------------------------|
| `preview`     | show what *would* move — touches nothing (default)       |
| `organize`    | perform the moves once, recording an undo manifest       |
| `watch_start` | start a background watcher (real-time, runs detached)    |
| `watch_stop`  | stop the background watcher                               |
| `status`      | is the watcher running? how many moves logged?           |
| `undo`        | reverse the most recent organize run                     |

Omit `folders` to use the defaults (Downloads, Desktop, Documents, Pictures),
or pass an explicit list like `["~/Downloads", "~/Desktop"]`.

## Using it from the CLI

```bash
# See the plan without moving anything
python -m tools.file_organizer preview ~/Downloads

# Organize once (asks for confirmation unless --yes)
python -m tools.file_organizer organize ~/Downloads --yes

# Real-time watcher in the foreground (Ctrl-C to stop)
python -m tools.file_organizer watch --folders ~/Downloads ~/Desktop

# Undo the last run / check status
python -m tools.file_organizer undo
python -m tools.file_organizer status
```

## Make it fully automatic (run at login)

Install a per-user auto-start entry so the watcher launches every time the user
logs in — launchd on macOS, Task Scheduler on Windows, systemd-user on Linux:

```bash
python -m tools.file_organizer install-autostart
# ...and to turn it off again:
python -m tools.file_organizer uninstall-autostart
```

## Configuration (optional)

Override defaults under `file_organizer:` in `config.yaml`:

```yaml
file_organizer:
  folders:
    - ~/Downloads
    - ~/Desktop
  # categories are extension-based; defaults cover the common types
```

## Recommended flow

1. `preview` the default folders and show the user the counts per category.
2. On approval, `organize` once.
3. If they want it ongoing, `watch_start` (or `install-autostart` for
   set-and-forget). Reassure them every move is reversible with `undo`.
