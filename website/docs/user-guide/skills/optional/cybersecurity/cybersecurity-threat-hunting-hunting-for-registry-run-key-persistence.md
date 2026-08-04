---
title: "Hunting For Registry Run Key Persistence — Detect MITRE ATT&CK T1547"
sidebar_label: "Hunting For Registry Run Key Persistence"
description: "Detect MITRE ATT&CK T1547"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Hunting For Registry Run Key Persistence

Detect MITRE ATT&CK T1547.001 registry Run key persistence by analyzing Sysmon Event ID 13 logs and registry queries to identify malicious auto-start entries.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/hunting-for-registry-run-key-persistence` |
| Path | `optional-skills/cybersecurity/threat-hunting/hunting-for-registry-run-key-persistence` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Hunting for Registry Run Key Persistence

## Overview

Registry Run keys (T1547.001) are one of the most commonly used persistence mechanisms by adversaries. When a program is added to a Run key in the Windows registry, it executes automatically when a user logs in. Attackers abuse keys under `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`, `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, and their RunOnce counterparts to maintain persistence. Sysmon Event ID 13 (RegistryEvent - Value Set) captures registry value modifications including the target object path, the process that made the change, and the new value. Detection involves monitoring these events for suspicious executables in temp directories, encoded PowerShell commands, LOLBin paths, and processes that do not normally create Run key entries. Chaining Event 13 with Event 1 (Process Creation) and Event 11 (FileCreate) strengthens detection by confirming payload creation and execution.


## When to Use

- When investigating security incidents that require hunting for registry run key persistence
- When building detection rules or threat hunting queries for this domain
- When SOC analysts need structured procedures for this analysis type
- When validating security monitoring coverage for related attack techniques

## Prerequisites

- Windows systems with Sysmon installed and configured to log Event ID 13
- Sysmon config with RegistryEvent rules for Run/RunOnce keys
- Python 3.9+ with `json`, `xml.etree.ElementTree`, `re` modules
- SIEM or log aggregator collecting Sysmon logs (Splunk, Elastic, Sentinel)
- Knowledge of legitimate auto-start programs for baseline comparison

## Steps

1. Collect Sysmon Event ID 13 logs filtered for Run/RunOnce key paths
2. Parse event XML/JSON for TargetObject, Details (value written), Image (modifying process)
3. Flag entries where the value points to temp directories, AppData, or ProgramData
4. Detect encoded PowerShell commands or script interpreters in registry values
5. Identify LOLBin abuse (mshta.exe, rundll32.exe, regsvr32.exe, wscript.exe)
6. Compare against known-good baseline of legitimate auto-start entries
7. Check if the modifying process (Image) is unusual (cmd.exe, powershell.exe, python.exe)
8. Chain with Event ID 1 to verify if the registered binary was recently created
9. Generate detection report with MITRE ATT&CK mapping and severity scores
10. Produce Sigma/Splunk detection rules from findings

## Expected Output

A JSON report listing suspicious Run key entries with the registry path, value written, modifying process, timestamp, MITRE technique mapping, severity rating, and recommended Sigma detection rules.

## Standards mapping

- **d3fend_techniques**: Executable Denylisting, Execution Isolation, File Metadata Consistency Validation, Content Format Conversion, File Content Analysis
- **nist_csf**: DE.CM-01, DE.AE-02, DE.AE-07, ID.RA-05
- **license**: Apache-2.0
- **author**: mahipal
