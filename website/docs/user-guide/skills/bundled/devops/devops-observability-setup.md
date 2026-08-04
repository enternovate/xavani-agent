---
title: "Observability Setup — Set up structured logging, metrics, and tracing for production systems"
sidebar_label: "Observability Setup"
description: "Set up structured logging, metrics, and tracing for production systems"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Observability Setup

Set up structured logging, metrics, and tracing for production systems.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/devops/observability-setup` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Observability Setup

> "You cannot fix what you cannot see. You cannot improve what you cannot measure."

## When to use

- Setting up a new service for production.
- Adding monitoring to an existing service.
- Investigating blind spots in current observability.

## Prerequisites

- Access to a metrics/logging backend (Prometheus, Datadog, CloudWatch, etc.).
- Understanding of key service SLIs.

## Steps

### 1. Structured logging

Use structured (JSON) logs, not free-form text:
```json
{"timestamp": "2025-06-01T12:00:00Z", "level": "error", "message": "Request failed", "request_id": "abc123", "user_id": "u456", "error": "timeout"}
```

Always include:
- Timestamp (ISO 8601).
- Log level.
- Request/trace ID.
- Relevant context (user, endpoint, etc.).

### 2. Metrics (RED method)

For every service, track:
- **Rate:** requests per second.
- **Errors:** error rate (% of failed requests).
- **Duration:** latency distribution (p50, p95, p99).

### 3. Distributed tracing

Propagate trace IDs across service boundaries:
- Generate trace ID at the edge.
- Pass via `X-Trace-Id` header.
- Log the trace ID in every service.

### 4. Health checks

- `/health` — basic liveness.
- `/health/ready` — readiness (dependencies connected).
- Return structured status with component checks.

### 5. Alerts

Alert on symptoms, not causes:
- Error rate > 1% for 5 minutes.
- p99 latency > 2s for 5 minutes.
- Health check failures for 2 minutes.

Do NOT alert on:
- CPU usage (unless it causes user impact).
- Disk space (unless it's about to fill).

### 6. Dashboards

Create dashboards that answer operator questions:
- "Is the service healthy?" → error rate, latency, throughput.
- "What's broken?" → error breakdown by endpoint.
- "Is it getting worse?" → trends over time.

## Verification

- All logs are structured with request IDs.
- RED metrics are collected and graphed.
- Alerts are configured for user-facing symptoms.
- Dashboards answer the 3 operator questions.
