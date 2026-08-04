---
title: "Performing Red Team With Covenant"
sidebar_label: "Performing Red Team With Covenant"
description: "Conduct red team operations using the Covenant C2 framework for authorized adversary simulation, including listener setup, grunt deployment, task execution, ..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Performing Red Team With Covenant

Conduct red team operations using the Covenant C2 framework for authorized adversary simulation, including listener setup, grunt deployment, task execution, and lateral movement tracking.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/performing-red-team-with-covenant` |
| Path | `optional-skills/cybersecurity/red-team/performing-red-team-with-covenant` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Performing Red Team Operations with Covenant C2

## Overview

Covenant is a collaborative .NET C2 framework for red teamers that provides a Swagger-documented REST API for managing listeners, launchers, grunts (agents), and tasks. This skill covers automating Covenant operations through its API for authorized red team engagements: creating HTTP/HTTPS listeners, generating binary and PowerShell launchers, deploying grunts, executing tasks on compromised hosts, and tracking lateral movement.


## When to Use

- When conducting security assessments that involve performing red team with covenant
- When following incident response procedures for related security events
- When performing scheduled security testing or auditing activities
- When validating security controls through hands-on testing

## Prerequisites

- Covenant C2 server deployed (Docker or .NET 6)
- Python 3.9+ with `requests` library
- Covenant API token (obtained via /api/users/login)
- Written authorization for red team engagement
- Isolated lab or authorized target environment

## Steps

### Step 1: Authenticate to Covenant API
Obtain a JWT token by posting credentials to /api/users/login endpoint.

### Step 2: Create Listener
Configure an HTTP or HTTPS listener with callback URLs and bind address.

### Step 3: Generate Launcher
Create a binary, PowerShell, or MSBuild launcher tied to the listener for grunt deployment.

### Step 4: Deploy and Manage Grunts
Monitor grunt callbacks, execute tasks, and collect output from compromised hosts.

### Step 5: Document Operations
Generate an operations report documenting all actions, timestamps, and findings.

## Expected Output

JSON report with listener configuration, active grunts, executed tasks, and task output for engagement documentation.

## Standards mapping

- **nist_csf**: ID.RA-01, GV.OV-02, DE.AE-07
- **license**: Apache-2.0
- **author**: mahipal
