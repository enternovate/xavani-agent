---
title: "Performing Active Directory Forest Trust Attack"
sidebar_label: "Performing Active Directory Forest Trust Attack"
description: "Enumerate and audit Active Directory forest trust relationships using impacket for SID filtering analysis, trust key extraction, cross-forest SID history abu..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Performing Active Directory Forest Trust Attack

Enumerate and audit Active Directory forest trust relationships using impacket for SID filtering analysis, trust key extraction, cross-forest SID history abuse detection, and inter-realm Kerberos ticket assessment.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/performing-active-directory-forest-trust-attack` |
| Path | `optional-skills/cybersecurity/red-team/performing-active-directory-forest-trust-attack` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Performing Active Directory Forest Trust Attack

## Overview

Active Directory forest trusts enable authentication across organizational boundaries but introduce attack surface if misconfigured. This skill uses impacket to enumerate trust relationships, analyze SID filtering configuration, detect SID history abuse vectors, perform cross-forest SID lookups via LSA/LSAT RPC calls, and assess inter-realm Kerberos ticket configurations for trust ticket forgery risks.


## When to Use

- When conducting security assessments that involve performing active directory forest trust attack
- When following incident response procedures for related security events
- When performing scheduled security testing or auditing activities
- When validating security controls through hands-on testing

## Prerequisites

- Python 3.9+ with `impacket`, `ldap3`
- Domain credentials with read access to AD trust objects
- Network access to Domain Controllers (ports 389, 445, 88)
- Authorized penetration testing engagement or lab environment


> **Legal Notice:** This skill is for authorized security testing and educational purposes only. Unauthorized use against systems you do not own or have written permission to test is illegal and may violate computer fraud laws.

## Steps

1. Enumerate forest trust relationships via LDAP trusted domain objects
2. Query trust attributes and SID filtering status for each trust
3. Perform SID lookups across trust boundaries using LsarLookupNames3
4. Enumerate foreign security principals in trusted domains
5. Check for SID history on cross-forest accounts
6. Assess trust direction and transitivity for lateral movement paths
7. Generate trust security audit report with risk findings

## Expected Output

- JSON report listing all trust relationships, SID filtering status, foreign principals, trust direction/transitivity, and risk assessment
- Cross-forest attack path analysis with remediation recommendations

## Standards mapping

- **nist_csf**: ID.RA-01, GV.OV-02, DE.AE-07
- **license**: Apache-2.0
- **author**: mahipal
