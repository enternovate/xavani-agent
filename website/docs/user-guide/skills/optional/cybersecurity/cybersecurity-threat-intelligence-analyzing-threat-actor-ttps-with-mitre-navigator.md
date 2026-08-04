---
title: "Analyzing Threat Actor Ttps With Mitre Navigator"
sidebar_label: "Analyzing Threat Actor Ttps With Mitre Navigator"
description: "Map advanced persistent threat (APT) group tactics, techniques, and procedures (TTPs) to the MITRE ATT&CK framework using the ATT&CK Navigator and attackcti ..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Analyzing Threat Actor Ttps With Mitre Navigator

Map advanced persistent threat (APT) group tactics, techniques, and procedures (TTPs) to the MITRE ATT&CK framework using the ATT&CK Navigator and attackcti Python library. The analyst queries STIX/TAXII data for group-technique associations, generates Navigator layer files for visualization, and compares defensive coverage against adversary profiles. Activates for requests involving APT TTP mapping, ATT&CK Navigator layers, threat actor profiling, or MITRE technique coverage analysis.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/analyzing-threat-actor-ttps-with-mitre-navigator` |
| Path | `optional-skills/cybersecurity/threat-intelligence/analyzing-threat-actor-ttps-with-mitre-navigator` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Analyzing Threat Actor TTPs with MITRE Navigator

## Overview

The MITRE ATT&CK Navigator is a web application for annotating and visualizing ATT&CK matrices.
Combined with the attackcti Python library (which queries ATT&CK STIX data via TAXII), analysts
can programmatically generate Navigator layer files mapping specific threat group TTPs, compare
multiple groups, and assess detection coverage gaps against known adversaries.


## When to Use

- When investigating security incidents that require analyzing threat actor ttps with mitre navigator
- When building detection rules or threat hunting queries for this domain
- When SOC analysts need structured procedures for this analysis type
- When validating security monitoring coverage for related attack techniques

## Prerequisites

- Python 3.8+ with attackcti and stix2 libraries installed
- MITRE ATT&CK Navigator (web UI or local instance)
- Understanding of STIX 2.1 objects and relationships

## Steps

1. Query ATT&CK STIX data for target threat group using attackcti
2. Extract techniques associated with the group via STIX relationships
3. Generate ATT&CK Navigator layer JSON with technique annotations
4. Overlay detection coverage to identify gaps
5. Export layer for team review and defensive planning

## Expected Output

```json
{
  "name": "APT29 TTPs",
  "domain": "enterprise-attack",
  "techniques": [
    {"techniqueID": "T1566.001", "score": 1, "comment": "Spearphishing Attachment"},
    {"techniqueID": "T1059.001", "score": 1, "comment": "PowerShell"}
  ]
}
```

## Standards mapping

- **d3fend_techniques**: File Metadata Consistency Validation, Application Protocol Command Analysis, Identifier Analysis, Content Format Conversion, Message Analysis
- **atlas_techniques**: AML.T0070, AML.T0066, AML.T0082
- **nist_ai_rmf**: MEASURE-2.7, MAP-5.1, MANAGE-2.4
- **nist_csf**: ID.RA-01, ID.RA-05, DE.CM-01, DE.AE-02
- **license**: Apache-2.0
- **author**: mahipal
