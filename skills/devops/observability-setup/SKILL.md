---
name: observability-setup
description: Set up structured logging, metrics, and tracing for production systems.
categories:
  - devops
platforms:
  - all
tags:
  - observability
  - logging
  - metrics
  - tracing
condition: When setting up monitoring for a new service or improving observability of an existing one.
---

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
