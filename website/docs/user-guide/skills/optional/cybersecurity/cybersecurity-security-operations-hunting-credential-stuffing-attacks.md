---
title: "Hunting Credential Stuffing Attacks"
sidebar_label: "Hunting Credential Stuffing Attacks"
description: "Detects credential stuffing attacks by analyzing authentication logs for login velocity anomalies, ASN diversity, password spray patterns, and geographic dis..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Hunting Credential Stuffing Attacks

Detects credential stuffing attacks by analyzing authentication logs for login velocity anomalies, ASN diversity, password spray patterns, and geographic distribution of failed logins. Uses statistical analysis on Splunk or raw log data. Use when investigating account takeover campaigns or building detection rules for auth abuse.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/hunting-credential-stuffing-attacks` |
| Path | `optional-skills/cybersecurity/security-operations/hunting-credential-stuffing-attacks` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Hunting Credential Stuffing Attacks


## When to Use

- When investigating security incidents that require hunting credential stuffing attacks
- When building detection rules or threat hunting queries for this domain
- When SOC analysts need structured procedures for this analysis type
- When validating security monitoring coverage for related attack techniques

## Prerequisites

- Familiarity with security operations concepts and tools
- Access to a test or lab environment for safe execution
- Python 3.8+ with required dependencies installed
- Appropriate authorization for any testing activities

## Instructions

Analyze authentication logs to detect credential stuffing by identifying patterns
of distributed login failures, high IP diversity, and suspicious ASN distribution.

```python
import pandas as pd
from collections import Counter

# Load auth logs
df = pd.read_csv("auth_logs.csv", parse_dates=["timestamp"])

# Credential stuffing indicator: many IPs trying few accounts
ip_per_account = df[df["status"] == "failed"].groupby("username")["source_ip"].nunique()
accounts_under_attack = ip_per_account[ip_per_account > 50]
```

Key detection indicators:
1. High unique source IPs per failed username
2. Low success rate across many accounts (&lt; 1%)
3. ASN concentration from cloud/proxy providers
4. Geographic impossibility (same account, distant locations)
5. User-agent uniformity across distributed IPs

## Examples

```python
# Password spray: one password tried across many accounts
spray = df[df["status"] == "failed"].groupby(["source_ip", "password_hash"]).agg(
    accounts=("username", "nunique")).reset_index()
sprays = spray[spray["accounts"] > 10]
```

## Standards mapping

- **nist_csf**: DE.CM-01, RS.MA-01, GV.OV-01, DE.AE-02
- **license**: Apache-2.0
- **author**: mahipal
