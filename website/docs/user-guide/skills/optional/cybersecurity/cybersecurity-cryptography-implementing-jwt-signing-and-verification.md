---
title: "Implementing Jwt Signing And Verification"
sidebar_label: "Implementing Jwt Signing And Verification"
description: "JSON Web Tokens (JWT) defined in RFC 7519 are compact, URL-safe tokens used for authentication and authorization in web applications"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Implementing Jwt Signing And Verification

JSON Web Tokens (JWT) defined in RFC 7519 are compact, URL-safe tokens used for authentication and authorization in web applications. This skill covers implementing secure JWT signing with HMAC-SHA256

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/implementing-jwt-signing-and-verification` |
| Path | `optional-skills/cybersecurity/cryptography/implementing-jwt-signing-and-verification` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Implementing JWT Signing and Verification

## Overview

JSON Web Tokens (JWT) defined in RFC 7519 are compact, URL-safe tokens used for authentication and authorization in web applications. This skill covers implementing secure JWT signing with HMAC-SHA256, RSA-PSS, and EdDSA algorithms, along with verification, token expiration, claims validation, and defense against common JWT attacks (algorithm confusion, none algorithm, key injection).


## When to Use

- When deploying or configuring implementing jwt signing and verification capabilities in your environment
- When establishing security controls aligned to compliance requirements
- When building or improving security architecture for this domain
- When conducting security assessments that require this implementation

## Prerequisites

- Familiarity with cryptography concepts and tools
- Access to a test or lab environment for safe execution
- Python 3.8+ with required dependencies installed
- Appropriate authorization for any testing activities

## Objectives

- Implement JWT signing with HS256, RS256, ES256, and EdDSA
- Verify JWT signatures and validate standard claims
- Implement token expiration, not-before, and audience validation
- Defend against algorithm confusion and none algorithm attacks
- Implement JWT key rotation with JWK Sets
- Build a complete authentication middleware

## Key Concepts

### JWT Algorithms

| Algorithm | Type | Key | Security Level |
|-----------|------|-----|---------------|
| HS256 | Symmetric (HMAC) | Shared secret | 128-bit |
| RS256 | Asymmetric (RSA) | RSA key pair | 112-bit |
| ES256 | Asymmetric (ECDSA) | P-256 key pair | 128-bit |
| EdDSA | Asymmetric (Ed25519) | Ed25519 pair | 128-bit |

### Common JWT Attacks

- **Algorithm confusion**: Switching from RS256 to HS256, using public key as HMAC secret
- **None algorithm**: Setting alg=none to bypass signature verification
- **Key injection**: Embedding key in JWK header
- **Weak secrets**: Brute-forcing short HMAC secrets
- **Token replay**: Reusing valid tokens without expiration

## Security Considerations

- Always validate the algorithm header against an allowlist
- Never accept alg=none in production
- Use asymmetric algorithms (RS256, ES256) for distributed systems
- Set short expiration times (15 min for access tokens)
- Implement token refresh mechanism
- Store secrets securely (not in source code)

## Validation Criteria

- [ ] JWT signing produces valid tokens for all algorithms
- [ ] Signature verification rejects tampered tokens
- [ ] Expired tokens are rejected
- [ ] Algorithm confusion attack is prevented
- [ ] None algorithm is rejected
- [ ] JWK key rotation works correctly
- [ ] Claims validation enforces all required claims

## Standards mapping

- **nist_csf**: PR.DS-01, PR.DS-02, PR.DS-10
- **license**: Apache-2.0
- **author**: mahipal
