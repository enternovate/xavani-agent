---
title: "Detecting Azure Storage Account Misconfigurations"
sidebar_label: "Detecting Azure Storage Account Misconfigurations"
description: "Audit Azure Blob and ADLS storage accounts for public access exposure, weak or long-lived SAS tokens, missing encryption at rest, disabled HTTPS-only traffic..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Detecting Azure Storage Account Misconfigurations

Audit Azure Blob and ADLS storage accounts for public access exposure, weak or long-lived SAS tokens, missing encryption at rest, disabled HTTPS-only traffic, and outdated TLS versions using the azure-mgmt-storage Python SDK.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/detecting-azure-storage-account-misconfigurations` |
| Path | `optional-skills/cybersecurity/cloud-security/detecting-azure-storage-account-misconfigurations` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Detecting Azure Storage Account Misconfigurations

## Overview

Azure Storage accounts are a frequent target for attackers due to misconfigured public access, long-lived SAS tokens, missing encryption, and outdated TLS versions. This skill uses the azure-mgmt-storage Python SDK with StorageManagementClient to enumerate all storage accounts in a subscription, inspect their security properties, list blob containers for public access settings, and generate a risk-scored audit report identifying critical misconfigurations.


## When to Use

- When investigating security incidents that require detecting azure storage account misconfigurations
- When building detection rules or threat hunting queries for this domain
- When SOC analysts need structured procedures for this analysis type
- When validating security monitoring coverage for related attack techniques

## Prerequisites

- Python 3.9+ with `azure-mgmt-storage`, `azure-identity`
- Azure service principal with Reader role on target subscription
- Environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID

## Key Detection Areas

1. **Public blob access** — `allow_blob_public_access` enabled on storage account or individual containers set to Blob/Container access level
2. **HTTPS enforcement** — `enable_https_traffic_only` disabled, allowing unencrypted HTTP traffic
3. **Minimum TLS version** — accounts accepting TLS 1.0 or TLS 1.1 instead of minimum TLS 1.2
4. **Encryption at rest** — storage service encryption not enabled or missing customer-managed keys
5. **Network rules** — default action set to Allow instead of Deny, exposing storage to all networks
6. **SAS token risks** — account-level SAS with overly broad permissions or excessive lifetime

## Output

JSON report with per-account findings, severity ratings (Critical/High/Medium/Low), and remediation recommendations aligned with CIS Azure Benchmark controls.

## Standards mapping

- **atlas_techniques**: AML.T0070, AML.T0066, AML.T0082
- **nist_ai_rmf**: MEASURE-2.7, MAP-5.1, MANAGE-2.4
- **nist_csf**: PR.IR-01, ID.AM-08, GV.SC-06, DE.CM-01
- **license**: Apache-2.0
- **author**: mahipal
