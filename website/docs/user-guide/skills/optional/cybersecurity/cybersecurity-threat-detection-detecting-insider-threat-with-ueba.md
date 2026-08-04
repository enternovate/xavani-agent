---
title: "Detecting Insider Threat With Ueba"
sidebar_label: "Detecting Insider Threat With Ueba"
description: "Implement User and Entity Behavior Analytics using Elasticsearch/OpenSearch to build behavioral baselines, calculate anomaly scores, perform peer group analy..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Detecting Insider Threat With Ueba

Implement User and Entity Behavior Analytics using Elasticsearch/OpenSearch to build behavioral baselines, calculate anomaly scores, perform peer group analysis, and detect insider threat indicators such as data exfiltration, privilege abuse, and unauthorized access patterns.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/detecting-insider-threat-with-ueba` |
| Path | `optional-skills/cybersecurity/threat-detection/detecting-insider-threat-with-ueba` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Detecting Insider Threat with UEBA

## Overview

User and Entity Behavior Analytics (UEBA) moves beyond static rule-based detection to model normal behavior for users, hosts, and applications, then flag statistically significant deviations that may indicate insider threats. Using Elasticsearch as the analytics backend, this skill covers building behavioral baselines from authentication logs, file access events, and network activity, computing risk scores using statistical deviation and peer group comparison, and correlating multiple low-confidence indicators into high-confidence insider threat alerts.


## When to Use

- When investigating security incidents that require detecting insider threat with ueba
- When building detection rules or threat hunting queries for this domain
- When SOC analysts need structured procedures for this analysis type
- When validating security monitoring coverage for related attack techniques

## Prerequisites

- Elasticsearch 8.x or OpenSearch 2.x cluster with security audit data
- Log sources: Active Directory authentication, VPN, DLP, file server access, email
- Python 3.9+ with elasticsearch client library
- Baseline period of 30+ days of normal user activity data
- Defined peer groups based on department, role, or job function

## Steps

### Step 1: Ingest and Normalize Activity Logs
Configure log pipelines to ingest authentication, file access, email, and network logs into Elasticsearch with a unified user identity field.

### Step 2: Build Behavioral Baselines
Calculate per-user baselines for login times, data volume, application usage, and access patterns over a rolling 30-day window using Elasticsearch aggregations.

### Step 3: Calculate Anomaly Scores
Compare current activity against baselines using z-score deviation and peer group comparison to generate per-user risk scores.

### Step 4: Correlate and Alert
Combine multiple anomalous indicators (unusual hours + large downloads + new system access) into composite risk scores that trigger SOC investigation workflows.

## Expected Output

JSON report containing per-user risk scores, anomalous activity details, peer group deviations, and recommended investigation actions.

## Standards mapping

- **nist_csf**: DE.CM-01, DE.AE-02, DE.AE-06, ID.RA-05
- **license**: Apache-2.0
- **author**: mahipal
