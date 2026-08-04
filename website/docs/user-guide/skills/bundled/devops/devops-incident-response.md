---
title: "Incident Response — Structured incident response — detect, triage, mitigate, resolve, and postmortem"
sidebar_label: "Incident Response"
description: "Structured incident response — detect, triage, mitigate, resolve, and postmortem"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Incident Response

Structured incident response — detect, triage, mitigate, resolve, and postmortem.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/devops/incident-response` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Incident Response

> "The goal is not to prevent all incidents — it is to resolve them fast and learn from them."

## When to use

- A production system is down or degraded.
- Users are reporting errors or slowness.
- Monitoring alerts have fired.

## Prerequisites

- Access to monitoring dashboards.
- Access to logs and traces.
- Communication channel (Slack, Teams, etc.).

## Steps

### 1. Detect and acknowledge

- Confirm the incident is real (not a monitoring glitch).
- Acknowledge in the communication channel.
- Assign an incident commander.

### 2. Assess severity

| Severity | Impact | Response time |
|----------|--------|---------------|
| SEV-1 | All users affected, data loss risk | Immediate |
| SEV-2 | Many users affected, degraded service | 15 minutes |
| SEV-3 | Some users affected, workaround exists | 1 hour |
| SEV-4 | Minor impact, cosmetic issues | Next business day |

### 3. Triage

- What changed recently? (deployments, config, infrastructure)
- What do the logs say?
- What do the metrics show?
- Is it a known failure mode?

### 4. Mitigate

Priority: restore service, then find root cause.
- Rollback the last deployment.
- Scale up resources.
- Enable circuit breakers.
- Redirect traffic.

### 5. Communicate

- Status updates every 15 minutes for SEV-1/2.
- ETA for resolution (even if "unknown").
- Impact description for stakeholders.

### 6. Resolve

- Confirm the fix works.
- Monitor for recurrence.
- Close the incident.

### 7. Postmortem (within 48 hours)

- Timeline of events.
- Root cause analysis.
- What went well.
- What could improve.
- Action items with owners and dates.

## Verification

- Incident is resolved and users are unblocked.
- Postmortem is written with action items.
- Action items are tracked to completion.
