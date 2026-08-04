---
title: "Implementing Deception Based Detection With Canarytoken"
sidebar_label: "Implementing Deception Based Detection With Canarytoken"
description: "Deploy and monitor Canary Tokens via the Thinkst Canary API for deception-based breach detection using web bug tokens, DNS tokens, document tokens, and AWS k..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Implementing Deception Based Detection With Canarytoken

Deploy and monitor Canary Tokens via the Thinkst Canary API for deception-based breach detection using web bug tokens, DNS tokens, document tokens, and AWS key tokens.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/implementing-deception-based-detection-with-canarytoken` |
| Path | `optional-skills/cybersecurity/deception-technology/implementing-deception-based-detection-with-canarytoken` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Implementing Deception-Based Detection with Canarytoken

## Overview

Canary Tokens are lightweight tripwire mechanisms that alert when an attacker accesses a resource. This skill uses the Thinkst Canary REST API to programmatically create tokens (web bugs, DNS tokens, MS Word documents, AWS API keys), deploy them to strategic locations, monitor for triggered alerts, and generate deception coverage reports.


## When to Use

- When deploying or configuring implementing deception based detection with canarytoken capabilities in your environment
- When establishing security controls aligned to compliance requirements
- When building or improving security architecture for this domain
- When conducting security assessments that require this implementation

## Prerequisites

- Thinkst Canary Console or canarytokens.org account
- API auth token from Canary Console
- Python 3.9+ with `requests`
- File system access for deploying document and file tokens

## Steps

1. Authenticate to the Canary Console API using auth_token
2. Create web bug (HTTP) tokens for embedding in documents and web pages
3. Create DNS tokens for monitoring DNS resolution attempts
4. Create MS Word document tokens for file share deployment
5. List all active tokens and their trigger history
6. Query recent alerts for triggered token events
7. Generate deception coverage report with deployment recommendations

## Expected Output

- JSON report listing all deployed Canary Tokens, trigger history, alert details, and coverage analysis
- Deployment map showing token types across network segments

## Standards mapping

- **nist_csf**: DE.CM-01, DE.AE-06, PR.IR-01
- **license**: Apache-2.0
- **author**: mahipal
