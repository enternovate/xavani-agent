---
title: "Hunting For Lateral Movement Via Wmi"
sidebar_label: "Hunting For Lateral Movement Via Wmi"
description: "Detect WMI-based lateral movement by analyzing Windows Event ID 4688 process creation and Sysmon Event ID 1 for WmiPrvSE"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Hunting For Lateral Movement Via Wmi

Detect WMI-based lateral movement by analyzing Windows Event ID 4688 process creation and Sysmon Event ID 1 for WmiPrvSE.exe child process patterns, remote process execution, and WMI event subscription persistence.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/hunting-for-lateral-movement-via-wmi` |
| Path | `optional-skills/cybersecurity/threat-hunting/hunting-for-lateral-movement-via-wmi` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Hunting for Lateral Movement via WMI

## Overview

Windows Management Instrumentation (WMI) is commonly abused for lateral movement via `wmic process call create` or Win32_Process.Create() to execute commands on remote hosts. Detection focuses on identifying WmiPrvSE.exe spawning child processes (cmd.exe, powershell.exe) in Windows Security Event ID 4688 and Sysmon Event ID 1 logs, along with WMI-Activity/Operational events (5857, 5860, 5861) for event subscription persistence.


## When to Use

- When investigating security incidents that require hunting for lateral movement via wmi
- When building detection rules or threat hunting queries for this domain
- When SOC analysts need structured procedures for this analysis type
- When validating security monitoring coverage for related attack techniques

## Prerequisites

- Windows Security Event Logs with Process Creation auditing enabled (Event 4688 with command line)
- Sysmon installed with Event ID 1 (Process Creation) configured
- Python 3.9+ with `python-evtx`, `lxml` libraries
- Understanding of WMI architecture and WmiPrvSE.exe behavior

## Steps

### Step 1: Parse Process Creation Events
Extract Event ID 4688 and Sysmon Event 1 entries from EVTX files.

### Step 2: Detect WmiPrvSE Child Processes
Flag processes where ParentImage/ParentProcessName is WmiPrvSE.exe, indicating remote WMI execution.

### Step 3: Analyze Command Line Patterns
Identify suspicious command lines matching WMI lateral movement patterns (cmd.exe /q /c, output redirection to admin$ share).

### Step 4: Check WMI Event Subscriptions
Parse WMI-Activity/Operational log for event consumer creation indicating persistence.

## Expected Output

JSON report with WMI-spawned processes, suspicious command lines, WMI event subscription alerts, and timeline of lateral movement activity.

## Standards mapping

- **nist_csf**: DE.CM-01, DE.AE-02, DE.AE-07, ID.RA-05
- **license**: Apache-2.0
- **author**: mahipal
