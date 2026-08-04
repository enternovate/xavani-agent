---
title: "Secure By Default Checklist — Security review checklist — verify every change follows secure-by-default principles"
sidebar_label: "Secure By Default Checklist"
description: "Security review checklist — verify every change follows secure-by-default principles"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Secure By Default Checklist

Security review checklist — verify every change follows secure-by-default principles.

## Skill metadata

| | |
|---|---|
| Source | Bundled (installed by default) |
| Path | `skills/software-development/secure-by-default-checklist` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Secure-by-Default Checklist

> "Security is not a feature — it is a property of every feature."

## When to use

- Any change that handles user input.
- Authentication or authorization changes.
- API endpoints that accept external data.
- File uploads, downloads, or processing.
- Database queries with user-provided values.

## Prerequisites

- Understanding of the OWASP Top 10.
- Access to the codebase.

## Steps

### 1. Input validation

- All user input is validated before use.
- Validation happens on the server (client-side is UX, not security).
- Use allowlists, not blocklists.
- Validate type, length, format, and range.

### 2. SQL injection

- Use parameterised queries or ORM.
- Never concatenate user input into SQL strings.
- Verify with: `grep -r "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" .`

### 3. XSS (Cross-Site Scripting)

- Escape all user content before rendering in HTML.
- Use templating engines that auto-escape.
- Set `Content-Security-Policy` headers.
- Use `HttpOnly` and `Secure` flags on cookies.

### 4. Authentication

- Passwords hashed with bcrypt/argon2 (never MD5/SHA1).
- Session tokens are random, long (>128 bits), and rotated.
- Rate limit login attempts.
- Multi-factor authentication available.

### 5. Authorization

- Check permissions on every request (not just at the UI level).
- Default to deny (whitelist, not blacklist).
- Principle of least privilege.
- Verify with: `grep -r "skip_auth\|no_auth\|public" .`

### 6. Secrets management

- No secrets in code or config files.
- Use environment variables or a secrets manager.
- Rotate secrets regularly.
- Verify with: `grep -rniE "password|secret|api_key|token" . --include="*.py" --include="*.js"`

### 7. HTTPS

- All external communication over HTTPS.
- HSTS headers set.
- No mixed content.

### 8. Dependencies

- No known critical vulnerabilities: `pip-audit` / `npm audit`.
- Dependencies pinned to specific versions.
- Regular dependency updates.

## Verification

- All 8 areas reviewed and passing.
- No secrets in code.
- Input validation on all endpoints.
- Parameterised queries everywhere.
