---
title: "Planner — Triage Gmail, extract action items into tasks, draft replies, and build one unified 'plan my day'"
sidebar_label: "Planner"
description: "Triage Gmail, extract action items into tasks, draft replies, and build one unified 'plan my day'"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Planner

Triage Gmail, extract action items into tasks, draft replies, and build one unified 'plan my day'.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/productivity/planner` |
| Version | `1.0.0` |
| Author | Enternovate |
| License | MIT |
| Platforms | linux, macos, windows |
| Tags | `Email`, `Planning`, `Productivity`, `Inbox`, `Tasks`, `Calendar` |
| Related skills | [`google-workspace`](/docs/user-guide/skills/bundled/productivity/productivity-google-workspace), [`himalaya`](/docs/user-guide/skills/bundled/email/email-himalaya), [`file-organizer`](/docs/user-guide/skills/bundled/productivity/productivity-file-organizer) |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# planner

Extends the "organize everything" idea from files (see the `file-organizer`
skill) to the user's **time and attention** — their inbox, tasks, calendar, and
the files needing tidying — pulled together into one prioritized plan.

Two agent tools:

- **`plan_emails`** — triage the inbox, extract action items into tasks, or draft replies.
- **`plan_day`** — one unified "plan my day" across email + calendar + tasks + files.

## Safety

Read + draft **only**. The planner never sends, deletes, archives, or modifies
mail. Drafting produces a *draft you review*; sending stays an explicit,
user-confirmed step via the google-workspace `gmail reply` command.

## `plan_emails` modes

| mode      | what it does                                                          |
|-----------|----------------------------------------------------------------------|
| `triage`  | Sort the inbox into **Action Required / Awaiting Reply / FYI / Newsletter / Receipt / Social**, ranked by urgency (default). |
| `actions` | Pull to-dos + deadlines out of action-required mail into the task list (`create_tasks=true`). |
| `draft`   | Produce reply **drafts** for action-required mail — never sends.       |

`query` accepts Gmail search syntax (e.g. `is:unread newer_than:2d`,
`from:boss@co.com`). Omit it for `in:inbox newer_than:7d`.

## `plan_day`

Merges, in priority order:

- **Schedule** — today's calendar events.
- **Top priorities** — email action items + open tasks, soonest-due first.
- **Inbox** — how many emails need action.
- **Files to tidy** — count from the file-organizer (nothing is moved).

It degrades gracefully: if Gmail/Calendar isn't connected it simply omits those
sections and still shows tasks + files.

## Prerequisites

Gmail/Calendar access comes from the **google-workspace** skill (one-time OAuth):

```bash
GSETUP="python ${XAVANI_HOME:-$HOME/.xavani}/skills/productivity/google-workspace/scripts/setup.py"
$GSETUP --check        # prints AUTHENTICATED when ready
```

If it isn't set up, `plan_emails` returns a clear "connect Gmail" message and
points at the setup. Generic IMAP via the `himalaya` skill also works.

## CLI

```bash
python -m tools.email_planner triage --query "is:unread" --max 25
python -m tools.email_planner actions
python -m tools.email_planner plan-day
```

## Recommended flow

1. `plan_emails` `triage` — show the user their inbox at a glance, ranked.
2. `plan_emails` `actions` — turn the must-dos into tasks.
3. `plan_emails` `draft` — offer drafts for the urgent ones (user sends).
4. `plan_day` — tie it together with calendar, tasks, and files into one plan.
