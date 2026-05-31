---
name: security-review
description: Security review checklist for code changes — authentication, authorization, input validation, secrets, and data protection.
categories:
  - software-development
platforms:
  - all
tags:
  - security
  - review
  - authentication
condition: When reviewing code that handles user data, authentication, or external input.
---

# Security Review

> "Security is not a feature you add. It is a property you verify."

## When to use

- Reviewing a PR that touches auth, data, or external input.
- Before deploying code that handles sensitive data.
- When adding a new API endpoint.

## Prerequisites

- Access to the code diff.
- Understanding of the system's trust boundaries.

## Steps

### 1. Authentication

- [ ] All endpoints require authentication (except public ones).
- [ ] Tokens are validated on every request.
- [ ] Token expiry is enforced.
- [ ] No credentials in code, config, or logs.

### 2. Authorization

- [ ] Permissions checked on every request (not just UI).
- [ ] Default is deny (whitelist, not blacklist).
- [ ] Users can only access their own resources.
- [ ] Admin actions require elevated permissions.

### 3. Input validation

- [ ] All user input validated server-side.
- [ ] Validation is allowlist-based (not blocklist).
- [ ] Type, length, format, and range checked.
- [ ] SQL queries use parameterised statements.
- [ ] HTML output is escaped.

### 4. Data protection

- [ ] Sensitive data encrypted at rest.
- [ ] Sensitive data encrypted in transit (TLS).
- [ ] PII is logged only when necessary (and masked).
- [ ] Data retention policies enforced.

### 5. Error handling

- [ ] Errors don't leak internal details.
- [ ] Stack traces not exposed to users.
- [ ] Error messages are generic but helpful.

### 6. Dependencies

- [ ] No known critical vulnerabilities.
- [ ] Dependencies pinned to versions.
- [ ] Unused dependencies removed.

## Verification

- All checklist items reviewed.
- No secrets in code.
- Input validated on all endpoints.
- Authorisation checked on all requests.


## Provenance

Xavani-original (written from scratch for Xavani, based on OWASP and common security review practices).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
