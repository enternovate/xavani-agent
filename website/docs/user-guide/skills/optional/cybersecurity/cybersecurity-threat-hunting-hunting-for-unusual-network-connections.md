---
title: "Hunting For Unusual Network Connections"
sidebar_label: "Hunting For Unusual Network Connections"
description: "Hunt for unusual network connections by analyzing outbound traffic patterns, rare destinations, non-standard ports, and anomalous connection frequencies from..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Hunting For Unusual Network Connections

Hunt for unusual network connections by analyzing outbound traffic patterns, rare destinations, non-standard ports, and anomalous connection frequencies from endpoints.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/hunting-for-unusual-network-connections` |
| Path | `optional-skills/cybersecurity/threat-hunting/hunting-for-unusual-network-connections` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Hunting For Unusual Network Connections

## When to Use

- When proactively hunting for indicators of hunting for unusual network connections in the environment
- After threat intelligence indicates active campaigns using these techniques
- During incident response to scope compromise related to these techniques
- When EDR or SIEM alerts trigger on related indicators
- During periodic security assessments and purple team exercises

## Prerequisites

- EDR platform with process and network telemetry (CrowdStrike, MDE, SentinelOne)
- SIEM with relevant log data ingested (Splunk, Elastic, Sentinel)
- Sysmon deployed with comprehensive configuration
- Windows Security Event Log forwarding enabled
- Threat intelligence feeds for IOC correlation

## Workflow

1. **Formulate Hypothesis**: Define a testable hypothesis based on threat intelligence or ATT&CK gap analysis.
2. **Identify Data Sources**: Determine which logs and telemetry are needed to validate or refute the hypothesis.
3. **Execute Queries**: Run detection queries against SIEM and EDR platforms to collect relevant events.
4. **Analyze Results**: Examine query results for anomalies, correlating across multiple data sources.
5. **Validate Findings**: Distinguish true positives from false positives through contextual analysis.
6. **Correlate Activity**: Link findings to broader attack chains and threat actor TTPs.
7. **Document and Report**: Record findings, update detection rules, and recommend response actions.

## Key Concepts

| Concept | Description |
|---------|-------------|
| T1071 | Application Layer Protocol |
| T1095 | Non-Application Layer Protocol |
| T1571 | Non-Standard Port |

## Tools & Systems

| Tool | Purpose |
|------|---------|
| CrowdStrike Falcon | EDR telemetry and threat detection |
| Microsoft Defender for Endpoint | Advanced hunting with KQL |
| Splunk Enterprise | SIEM log analysis with SPL queries |
| Elastic Security | Detection rules and investigation timeline |
| Sysmon | Detailed Windows event monitoring |
| Velociraptor | Endpoint artifact collection and hunting |
| Sigma Rules | Cross-platform detection rule format |

## Common Scenarios

1. **Scenario 1**: Backdoor communicating to C2 on non-standard port
2. **Scenario 2**: Data exfiltration over DNS to attacker nameserver
3. **Scenario 3**: Compromised host scanning internal network
4. **Scenario 4**: Cryptominer connecting to mining pool

## Output Format

```
Hunt ID: TH-HUNTIN-[DATE]-[SEQ]
Technique: T1071
Host: [Hostname]
User: [Account context]
Evidence: [Log entries, process trees, network data]
Risk Level: [Critical/High/Medium/Low]
Confidence: [High/Medium/Low]
Recommended Action: [Containment, investigation, monitoring]
```

## Standards mapping

- **d3fend_techniques**: File Metadata Consistency Validation, Certificate Analysis, Application Protocol Command Analysis, Content Format Conversion, File Content Analysis
- **nist_csf**: DE.CM-01, DE.AE-02, DE.AE-07, ID.RA-05
- **license**: Apache-2.0
- **author**: mahipal
