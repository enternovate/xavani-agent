---
name: incident-response
description: Structured incident response — detect, triage, mitigate, resolve, and postmortem.
categories:
  - devops
platforms:
  - all
tags:
  - incident
  - reliability
  - oncall
condition: When a production incident is detected or reported.
---

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
