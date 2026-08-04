---
title: "Performing Network Traffic Analysis With Tshark"
sidebar_label: "Performing Network Traffic Analysis With Tshark"
description: "Automate network traffic analysis using tshark and pyshark for protocol statistics, suspicious flow detection, DNS anomaly identification, and IOC extraction..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Performing Network Traffic Analysis With Tshark

Automate network traffic analysis using tshark and pyshark for protocol statistics, suspicious flow detection, DNS anomaly identification, and IOC extraction from PCAP files

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/performing-network-traffic-analysis-with-tshark` |
| Path | `optional-skills/cybersecurity/network-security/performing-network-traffic-analysis-with-tshark` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Performing Network Traffic Analysis with TShark

## Overview

This skill automates packet capture analysis using tshark (Wireshark CLI) and pyshark (Python wrapper). It extracts protocol distribution statistics, identifies suspicious network flows (port scans, beaconing, data exfiltration), extracts IOCs (IPs, domains, URLs), and detects DNS tunneling patterns from PCAP files.


## When to Use

- When conducting security assessments that involve performing network traffic analysis with tshark
- When following incident response procedures for related security events
- When performing scheduled security testing or auditing activities
- When validating security controls through hands-on testing

## Prerequisites

- tshark (Wireshark CLI) installed and in PATH
- Python 3.8+ with pyshark library
- PCAP or PCAPNG capture file for analysis

## Steps

1. **Extract Protocol Statistics** — Generate protocol hierarchy and conversation statistics from the capture
2. **Identify Top Talkers** — Rank source/destination IPs by volume and connection count
3. **Detect Suspicious Flows** — Flag port scanning patterns, unusual port usage, and high-frequency connections
4. **Extract Network IOCs** — Pull unique IPs, domains from DNS queries, and URLs from HTTP traffic
5. **Analyze DNS Traffic** — Detect DNS tunneling via high-entropy subdomain queries and excessive TXT records
6. **Generate Analysis Report** — Produce structured report with flow summaries and threat indicators

## Expected Output

- JSON report with protocol statistics and top talkers
- Suspicious flow detections with severity ratings
- Extracted IOCs (IPs, domains, URLs)
- DNS anomaly analysis results

## Standards mapping

- **nist_csf**: PR.IR-01, DE.CM-01, ID.AM-03, PR.DS-02
- **license**: Apache-2.0
- **author**: mahipal
